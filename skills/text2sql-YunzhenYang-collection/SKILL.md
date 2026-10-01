---
name: text2sql-YunzhenYang-collection
description: Convert a natural-language question + SQLite schema into one verified read-only SQL query. AIASE 2026 Basic Track.
version: 0.1.0
metadata:
  hermes:
    tags: [sql, text2sql, data, aiase-2026]
    category: data
---

# Text2SQL Skill

## When to Use

When the input is a JSON object with `question`, `db_schema` (SQLite DDL), optional `task_id`, and optional `dialect`. The skill produces a single read-only SQLite query whose result matches the gold answer under bag equality.

Trigger example:

```
/text2sql-YunzhenYang-collection {"task_id":"task_nl2sql_017",
  "question":"List the names of all students who scored above 90 ...",
  "db_schema":"CREATE TABLE Students(...); ...", "dialect":"sqlite"}
```

## Procedure

1. Parse `task_id`, `question`, `db_schema`, `dialect`.
2. Draft exactly one SQLite `SELECT` query. Keep it read-only and single-statement.
3. Validate immediately. Do not search files.

```bash
python skills/text2sql-YunzhenYang-collection/scripts/validate_sql.py '{"schema_ddl":"<db_schema>","sql":"<sql>"}'
```

If validation fails, fix the SQL and retry. Retry at most 2 times.

4. Write the final result file immediately by running `scripts/run.py`. Do not
   print or hand-write a JSON answer in the conversation.

```bash
python skills/text2sql-YunzhenYang-collection/scripts/run.py '{"task_id":"<task_id>","sql":"<sql>","rationale":"<one sentence>","confidence":<0.0-1.0>}'
```
After the command succeeds, stop. The grader reads the file at
`AIASE_RESULT_PATH`; no final JSON block is needed in the chat.

## SQL Rules

- SQLite only.
- `SELECT` only. No `INSERT`, `UPDATE`, `DELETE`, DDL, `PRAGMA`, or multiple statements.
- No `WITH`, recursive queries, or window functions.
- Use only tables and columns from `db_schema`.
- Use `DISTINCT` when the question asks for a set/list of entities and joins may duplicate rows.
- Use `COUNT(DISTINCT entity_id_or_name)` when counting unique entities across joins; use `COUNT(*)` only when counting rows/events.
- Use `GROUP BY ... HAVING` for questions asking "at least", "more than", "number of", or aggregate conditions per entity.
- Use `ORDER BY ... LIMIT n` for highest/lowest/top/bottom/most/least questions. Add a deterministic secondary sort only when the question or schema implies ties must be broken.
- Use `NOT EXISTS` or `LEFT JOIN ... IS NULL` for "without", "never", "no", or anti-join questions. Prefer `NOT EXISTS` when a nullable column could make `NOT IN` unsafe.
- For yes/no filters over related rows, use `EXISTS` to avoid accidental duplicate rows.
- Select only the columns requested by the question; do not add helper IDs unless the question asks for them.
- Preserve bag semantics: result row order does not matter, but duplicate rows do. Add `DISTINCT` only when the natural language asks for unique entities.
- Preserve the input `task_id` exactly.

## Verification

The result file written by `scripts/run.py` is a JSON object with:

- `task_id` (must equal input)
- `sql` (single read-only SQLite query)
- `rationale` (string)
- `confidence` (number in `[0.0, 1.0]`)

The script writes to `AIASE_RESULT_PATH`, or `./aiase_result.json` if that
environment variable is not set.
