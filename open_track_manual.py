import subprocess, json, sys, pathlib

SCRIPT = pathlib.Path("skills/open-sql-result-diff-YunzhenYang-collection/scripts/run.py")

def run(payload):
    r = subprocess.run(
        [sys.executable, str(SCRIPT), json.dumps(payload)],
        capture_output=True, text=True
    )
    print(r.stdout)
    if r.stderr:
        print("STDERR:", r.stderr)

# Scenario 1 — 非等價
run({
    "task_id": "diff_001",
    "db_schema": "CREATE TABLE orders (id INT, amount FLOAT, status TEXT);",
    "db_seed": "INSERT INTO orders VALUES (1, 50.0, 'paid'), (2, 30.0, 'pending'), (3, 80.0, 'paid');",
    "sql_a": "SELECT id FROM orders WHERE status = 'paid'",
    "sql_b": "SELECT id FROM orders WHERE amount > 60 AND status = 'paid'"
})

# Scenario 2 — 等價（含 ORDER BY）
run({
    "task_id": "diff_eq",
    "db_schema": "CREATE TABLE orders (id INT, amount FLOAT, status TEXT);",
    "db_seed": "INSERT INTO orders VALUES (1, 50.0, 'paid'), (2, 30.0, 'pending'), (3, 80.0, 'paid');",
    "sql_a": "SELECT id FROM orders WHERE status = 'paid' ORDER BY id DESC",
    "sql_b": "SELECT id FROM orders WHERE status = 'paid'"
})

# Scenario 3 — Multiset duplicate
run({
    "task_id": "diff_dupes",
    "db_schema": "CREATE TABLE t (x INT);",
    "db_seed": "INSERT INTO t VALUES (1), (1), (2);",
    "sql_a": "SELECT x FROM t WHERE x=1",
    "sql_b": "SELECT x FROM t WHERE x=1 LIMIT 1"
})

# Scenario 4 — Column mismatch
run({
    "task_id": "diff_cols",
    "db_schema": "CREATE TABLE users (id INT, name TEXT);",
    "db_seed": "INSERT INTO users VALUES (1, 'Ada');",
    "sql_a": "SELECT id, name FROM users",
    "sql_b": "SELECT id FROM users"
})

# Scenario 5 — SQL execution error
run({
    "task_id": "diff_err",
    "db_schema": "CREATE TABLE orders (id INT, status TEXT);",
    "db_seed": "INSERT INTO orders VALUES (1, 'paid');",
    "sql_a": "SELECT nonexistent_col FROM orders",
    "sql_b": "SELECT id FROM orders"
})
