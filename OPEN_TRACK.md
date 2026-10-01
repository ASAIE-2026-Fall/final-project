<!--
   Open Track 宣告 — 七個 heading 請照抄,順序也別動。
   合規判定會自動解析這七節;少一節就 fail gate。
   詳細要求見規格書 §2.4 與 §4.3。
-->

## 1. Skill 簡介

`open-sql-result-diff-YunzhenYang-collection` executes two SQL queries against the same in-memory SQLite schema and seed data, compares their result sets as multisets, and returns a deterministic machine-checkable diff summary.

## 2. Skill 名稱與目錄

- Skill name: `open-sql-result-diff-YunzhenYang-collection`
- Skill path: `skills/open-sql-result-diff-YunzhenYang-collection/`

## 3. 呼叫方式

**Slash command:**

```
/open-sql-result-diff-YunzhenYang-collection
```

**輸入 JSON 範例:**

```json
{
  "task_id": "diff_001",
  "db_schema": "CREATE TABLE orders (id INT, amount FLOAT, status TEXT);",
  "db_seed": "INSERT INTO orders VALUES (1, 50.0, 'paid'), (2, 30.0, 'pending'), (3, 80.0, 'paid');",
  "sql_a": "SELECT id FROM orders WHERE status = 'paid'",
  "sql_b": "SELECT id FROM orders WHERE amount > 60 AND status = 'paid'"
}
```

**預期輸出 JSON schema 範例:**

```json
{
  "task_id": "diff_001",
  "equivalent": false,
  "columns_a": ["id"],
  "columns_b": ["id"],
  "rows_only_in_a": [{"id": 1}],
  "rows_only_in_b": [],
  "rows_only_in_a_total": 1,
  "rows_only_in_b_total": 0,
  "diff_rows_truncated": false,
  "diff_type": "row_multiset_mismatch",
  "witness": {"type": "row_only_in_a", "side": "sql_a", "row": {"id": 1}},
  "execution_mode": "isolated_read_only",
  "value_normalization": {
    "integral_float_as_int": true,
    "blob_encoding": "hex",
    "duplicate_column_suffix": "#<position>"
  },
  "row_count_a": 2,
  "row_count_b": 1,
  "rationale": "Result sets differ: 1 rows appear only in sql_a, 0 rows appear only in sql_b.",
  "error": "",
  "confidence": 1.0
}
```

**完整呼叫方式（供 judge 推導）:**

Hermes 收到上方 slash command + JSON payload 後，SKILL.md 指示 agent 以
argv 方式執行 repo-relative `skills/open-sql-result-diff-YunzhenYang-collection/scripts/run.py`，script 將結果寫入 `AIASE_RESULT_PATH`，
評分器直接讀取該檔案，不從對話輸出擷取。例如：

```bash
python skills/open-sql-result-diff-YunzhenYang-collection/scripts/run.py '<payload_json>'
```

`run.py` 也支援 stdin pipe（`echo '<payload>' | python skills/open-sql-result-diff-YunzhenYang-collection/scripts/run.py`），兩種方式皆可。

## 4. 自定 Verifiable Scenario

此 Open Track 使用 deterministic SQLite execution 與 result-bag comparison。
Ground truth 由 Python 標準庫 `sqlite3` 實際執行 `db_schema`、`db_seed`、`sql_a`、`sql_b` 後決定；
評分器可獨立重跑相同規則：比較 column names，並用 multiset diff 比較 rows。

**Scenarios (至少 3 個):**

- Scenario 1 — 差異存在：
  - Schema: `orders(id INT, amount FLOAT, status TEXT)`
  - Seed: `(1, 50.0, 'paid'), (2, 30.0, 'pending'), (3, 80.0, 'paid')`
  - `sql_a`: `SELECT id FROM orders WHERE status = 'paid'`（回傳 id=1, id=3）
  - `sql_b`: `SELECT id FROM orders WHERE amount > 60 AND status = 'paid'`（回傳 id=3）
  - 預期：`equivalent=false`、`row_count_a=2`、`row_count_b=1`、`rows_only_in_a=[{"id":1}]`

- Scenario 2 — 等價但含 ORDER BY：
  - Schema: 同上
  - Seed: 同上
  - `sql_a`: `SELECT id FROM orders WHERE status = 'paid' ORDER BY id DESC`
  - `sql_b`: `SELECT id FROM orders WHERE status = 'paid'`
  - 預期：`equivalent=true`、`row_count_a=2`、`row_count_b=2`、diff rows 皆為空
  - 說明：multiset 比較不計 row 順序，ORDER BY 不影響等價判定

- Scenario 3 — Column mismatch：
  - Schema: `users(id INT, name TEXT)`
  - Seed: `(1, 'Alice'), (2, 'Bob')`
  - `sql_a`: `SELECT id, name FROM users`
  - `sql_b`: `SELECT id FROM users`
  - 預期：`equivalent=false`、`columns_a=["id","name"]`、`columns_b=["id"]`

- Scenario 4 — 重複列 multiset 差異：
  - Schema: `t(id INT)`
  - Seed: `(1), (1), (2)`
  - `sql_a`: `SELECT id FROM t`（回傳 id=1, id=1, id=2）
  - `sql_b`: `SELECT id FROM t WHERE rowid IN (1, 3)`（回傳 id=1, id=2）
  - 預期：`equivalent=false`、`row_count_a=3`、`row_count_b=2`、`rows_only_in_a=[{"id":1}]`
  - 說明：result diff 採 multiset/bag equality，重複列次數會被計入

- Scenario 5 — SQL 執行錯誤：
  - Schema: `orders(id INT, status TEXT)`
  - Seed: `INSERT INTO orders VALUES (1, 'paid');`
  - `sql_a`: `SELECT nonexistent_col FROM orders`（參照不存在的欄位）
  - `sql_b`: `SELECT id FROM orders`
  - 預期：`equivalent=false`、`error` 以 `sql_a_error:` 開頭、`columns_b=["id"]`、`row_count_b=1`、`confidence=0.0`

- Scenario 6 — Side-effect isolation：
  - Schema: `t(id INT)`
  - Seed: `(1), (2)`
  - `sql_a`: `DELETE FROM t`（嘗試修改資料）
  - `sql_b`: `SELECT id FROM t`
  - 預期：`equivalent=false`、`error` 以 `sql_a_error:` 開頭、`columns_b=["id"]`、`row_count_b=2`
  - 說明：`sql_a` 與 `sql_b` 在 isolated read-only DB copies 上執行，寫入型 SQL 不能污染另一邊的結果

**Metric:**

對每個 scenario，評分器判定 pass 的條件如下（全部須符合）：

1. `task_id` 與輸入完全一致（string equal）
2. `equivalent` 與 ground truth 一致（boolean equal）
3. `columns_a` 與 `columns_b` 與 ground truth 一致（ordered list equal）
4. `row_count_a` 與 `row_count_b` 與 ground truth 一致（integer equal）
5. `rows_only_in_a` 與 `rows_only_in_b` 與 ground truth 以 **bag equality** 比對（row 順序不計，重複次數計入）
6. `rows_only_in_a_total`、`rows_only_in_b_total` 與完整 diff count 一致；若 diff rows 超過 100 筆，`diff_rows_truncated=true`
7. `diff_type` 與主要結果類型一致，例如 `equivalent`、`row_multiset_mismatch`、`column_mismatch`、`sql_error`、`sql_timeout`
8. `witness` 為最小反例：row diff 時指向第一筆差異 row，column mismatch 時列出兩邊欄位，error/timeout 時列出錯誤摘要
9. `execution_mode` 固定為 `isolated_read_only`；`value_normalization` 說明 integral float、BLOB、duplicate column 的 canonical policy
10. `error` 欄位：成功時為空字串；執行錯誤時以 `schema_error:`、`seed_error:`、`sql_a_error:`、`sql_b_error:`、`sql_a_timeout:` 或 `sql_b_timeout:` 開頭（prefix match，不綁死完整 message）
11. `confidence`：成功時為 `1.0`，執行錯誤時為 `0.0`

**為何不可 gameable:**

- Staff 可任意變更 seed 數值、WHERE 條件、SELECT projection、重複列數量、task_id。
- 正確答案由 SQLite interpreter 決定，學生無法預知並 hardcode。
- `equivalent` 是 boolean，隨機猜測期望得分 50%；搭配 row counts 與 diff rows 的完整比對，實際期望得分遠低於真正執行 diff 的 skill。
- `witness` 提供最小反例，讓 grader 或人工 reviewer 不必掃完整 diff 就能確認失敗原因。
- `sql_a` 與 `sql_b` 使用同一份 base DB clone 出來的 isolated read-only copies 執行，side-effect SQL 無法污染另一邊。
- SQLite progress handler 會中止過重查詢，避免 recursive CTE 或巨大 join 卡死評分流程。
- `value_normalization` 採 SQLite-friendly policy：整數型 float 視為 int、BLOB 以 hex 表示、duplicate column 以 position suffix 輸出。
- `rows_only_in_a` / `rows_only_in_b` 最多各輸出前 100 筆差異，完整差異數保存在 `rows_only_in_a_total` / `rows_only_in_b_total`，避免大型 seed 造成結果檔過大。
- 所有欄位皆可程式化比對，無主觀判斷成分。

## 5. 預期失敗模式

- 失敗 1：SQL 執行錯誤（MAST: 驗證與品質）
  - 觸發點：`db_schema` 語法錯誤、`sql_a` 或 `sql_b` 參照不存在的欄位、或 `db_seed` 違反 schema 約束。
  - 處理：`scripts/run.py` 以 `try/except sqlite3.Error` 捕捉，emit 合法 JSON contract，`equivalent=false`、`error` 欄位填 `schema_error:`、`seed_error:`、`sql_a_error:` 或 `sql_b_error:`，`confidence=0.0`，不 crash 也不輸出 traceback。若只有 `sql_a` 或 `sql_b` 其中一邊失敗，另一邊成功取得的 columns 與 row count 仍會保留。

- 失敗 2：Column mismatch 導致無法做 row 比對（MAST: 規格與角色 / 驗證與品質）
  - 觸發點：`sql_a` 與 `sql_b` 回傳的 column names 或 column 順序不同（例如 `SELECT id, name` vs `SELECT name, id`）。
  - 處理：harness 在 column 比對失敗時立即回傳 `equivalent=false`，並輸出 `columns_a` / `columns_b` 供人工核查，不進行 row 層級比對（保守定義，避免誤判等價）。

- 失敗 3：昂貴查詢或 side-effect SQL（MAST: 安全與資源控制 / 驗證與品質）
  - 觸發點：recursive CTE、巨大 join、或 `INSERT` / `UPDATE` / `DELETE` / `DROP` 等非 read-only 操作。
  - 處理：每個 query 在 isolated read-only DB copy 上執行，並使用 SQLite progress handler 設定步數上限；超限會回傳 `sql_a_timeout:` 或 `sql_b_timeout:`，寫入型 SQL 會回傳對應的 `sql_a_error:` / `sql_b_error:`。

## 6. 互動對象

此 skill 設計為接收 Basic Track `/text2sql-YunzhenYang-collection` 的輸出 SQL 作為 `sql_a`，
並由 staff 或使用者提供 reference SQL 作為 `sql_b`，在相同 schema 與 seed 上執行 diff。

互動流程：
1. Hermes 呼叫 `/text2sql-YunzhenYang-collection`，取得 candidate SQL（`sql_a`）。
2. Hermes 呼叫 `/open-sql-result-diff-YunzhenYang-collection`，傳入 `sql_a`、reference `sql_b`、以及相同的 `db_schema` 與 `db_seed`。
3. diff skill 回傳 deterministic JSON，顯示兩段 SQL 的結果差異。

此三步驟形成完整的 NL → candidate SQL → regression verification pipeline，
interaction log 中可見明確的跨 skill 資料流。不使用 subagent，亦不依賴任何外部服務或網路。

## 7. Token Budget 估算

| Scenario | 預估 input tokens | 預估 output tokens | 預估 total |
|---|---:|---:|---:|
| Scenario 1 | 130 | 120 | 250 |
| Scenario 2 | 130 | 110 | 240 |
| Scenario 3 | 110 | 110 | 220 |
| Scenario 4 | 90 | 100 | 190 |
| Scenario 5 | 100 | 90 | 190 |
| Scenario 6 | 90 | 90 | 180 |
