---
name: open-sql-result-diff-YunzhenYang-collection
description: Execute two SQL queries against the same in-memory SQLite database and deterministically compare their result sets as multisets.
version: 0.1.0
metadata:
  hermes:
    tags: [sqlite, sql, diff, aiase-2026, open-track]
    category: data
---

# SQL Result Diff Analyzer Skill (Open Track)

## When to Use

Use this skill when the user provides a JSON payload with `task_id`, `db_schema`, `db_seed`, `sql_a`, and `sql_b`, and wants to verify whether the two SQL queries produce equivalent result sets on the same SQLite database.

This skill is designed to follow the Basic Track Text2SQL skill: Basic Track can generate a candidate SQL query, and this Open Track skill can compare that query against a reference SQL query.

Trigger example:

```
/open-sql-result-diff-YunzhenYang-collection {"task_id":"diff_001","db_schema":"CREATE TABLE orders (id INT, amount FLOAT, status TEXT);","db_seed":"INSERT INTO orders VALUES (1, 50.0, 'paid'), (2, 30.0, 'pending'), (3, 80.0, 'paid');","sql_a":"SELECT id FROM orders WHERE status = 'paid'","sql_b":"SELECT id FROM orders WHERE amount > 60 AND status = 'paid'"}
```

## Procedure

1. Parse the input payload. Confirm the five required fields are present by
   echoing a one-line summary, for example:
   `[open-sql-diff] task_id=<task_id> | sql_a=<first 40 chars>... | sql_b=<first 40 chars>...`
   If any of `task_id`, `db_schema`, `db_seed`, `sql_a`, or `sql_b` is missing,
   or if `task_id`, `db_schema`, `sql_a`, or `sql_b` is empty, stop and report
   the missing field; do not call `run.py` with an incomplete payload. `db_seed`
   must be present but may be an empty string when no seed data is needed.

2. Treat `db_schema`, `db_seed`, `sql_a`, and `sql_b` as SQLite strings.
   Do not rewrite, repair, or optimize either SQL query.

3. Run the command below with the original payload as a JSON argv.

```bash
python skills/open-sql-result-diff-YunzhenYang-collection/scripts/run.py '<original input payload JSON>'
```

4. Read the one-line `written ok -> <path>` confirmation printed by the script.
   If the script exits with a non-zero code, report the stderr output; do not
   retry automatically.

5. Stop. Do not hand-write a JSON answer in the conversation; the grader reads
   the result file.

## Pitfalls

- Do not infer SQL meaning from natural language.
- Do not rewrite, repair, or optimize either SQL query.
- Do not generate rationale text manually; the script emits deterministic template-based rationale.
- Do not ignore duplicate rows. Result sets are compared as multisets, not sets.
- Column names must match exactly and in order for result sets to be equivalent.
- `sql_a` and `sql_b` are executed on isolated read-only database copies so
  attempted writes cannot affect the other query.
- SQL or setup errors must produce a valid JSON result file, not a traceback.
- Do not add a fenced JSON block in the final chat response.

## Verification

The result file written by `scripts/run.py` must be a JSON object with:

- `task_id`: copied exactly from the input.
- `equivalent`: boolean, true only when both queries return identical column names in the same order and identical row multisets.
- `columns_a`: array of column names returned by `sql_a`, or `[]` if `sql_a` fails before producing columns.
- `columns_b`: array of column names returned by `sql_b`, or `[]` if `sql_b` fails before producing columns.
- `rows_only_in_a`: rows whose multiset count is greater in `sql_a` than in `sql_b`.
- `rows_only_in_b`: rows whose multiset count is greater in `sql_b` than in `sql_a`.
- `row_count_a`: number of rows returned by `sql_a`.
- `row_count_b`: number of rows returned by `sql_b`.
- `rows_only_in_a_total`: full count of rows only in `sql_a`, before truncating the displayed sample.
- `rows_only_in_b_total`: full count of rows only in `sql_b`, before truncating the displayed sample.
- `diff_rows_truncated`: boolean, true when either displayed diff row array was truncated.
- `diff_type`: machine-readable category such as `equivalent`, `row_multiset_mismatch`,
  `column_mismatch`, `sql_error`, `sql_timeout`, `schema_error`, `seed_error`, or `input_error`.
- `witness`: null when equivalent; otherwise a compact machine-readable counterexample,
  such as the first differing row, mismatched column lists, or the SQL error summary.
- `execution_mode`: `isolated_read_only`, indicating both queries ran on isolated read-only database copies.
- `value_normalization`: policy metadata for numeric, BLOB, and duplicate-column canonicalization.
- `rationale`: deterministic template text describing equivalence, column mismatch, result diff, or execution error.
- `error`: empty string on success, otherwise a deterministic error category and message.
- `confidence`: number in `[0.0, 1.0]`; this deterministic script emits `1.0`
  for completed comparisons and `0.0` for setup, input, or SQL execution errors.

The script writes to `AIASE_RESULT_PATH`, or `./aiase_result.json` if that
environment variable is not set.
