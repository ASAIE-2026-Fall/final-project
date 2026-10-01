# Basic Track Dev Set

20 NL→SQL tasks across 5 schemas. Their difficulty distribution mirrors the hidden test set used at grading.

## How to materialize the SQLite files

```bash
python dev_set/basic/build_dbs.py
```

This generates one `dbs/<task_id>.sqlite` per task. They are NOT committed (excluded by `.gitignore`); rebuild any time by re-running the script. Schemas + data are embedded in `build_dbs.py`.

## Coverage of the difficulty envelope (spec §2.2)

| Feature | Tasks |
|---|---|
| JOIN (≥ 2 tables) | 001, 002, 005, 007, 009, 013, 014 |
| LEFT JOIN | 006, 010, 017 |
| GROUP BY / HAVING | 002, 003, 007, 010, 014, 015, 017 |
| Aggregation (COUNT/SUM/AVG/MAX/MIN) | 002, 003, 007, 010, 014, 015, 017 |
| ORDER BY + LIMIT | 002, 007, 018 |
| UNION / UNION ALL | 008, 019 |
| Nested subquery (depth ≤ 2) | 004, 012, 015, 020 |
| Correlated subquery (NOT EXISTS) | 016, 020 |
| DISTINCT | 005, 008, 011, 018, 019 |
| NULL filter | 006 |

## Out of scope (will NOT appear in hidden set)

- window functions (`OVER(...)`)
- CTE (`WITH ... AS`)
- recursive queries
- DDL / DML
- non-SQLite dialect syntax

If you find any of these in this dev set, please file an issue — that would be a bug.

## Self-test integrity

`python run_dev.py --check-only` does *not* call any LLM; it just confirms:
1. each `gold_sql` parses and executes on its `db_path`,
2. `bag_equal(gold_rows, gold_rows)` is reflexively true,
3. no `gold_sql` strays out of the read-only / single-statement envelope.
