import json
import os
import subprocess
import sys
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "skills" / "open-sql-result-diff-YunzhenYang-collection" / "scripts" / "run.py"


def run_open_track(payload):
    result_root = REPO_ROOT / "dev_run_results"
    result_root.mkdir(exist_ok=True)
    result_path = result_root / f"open_track_test_result_{uuid.uuid4().hex}.json"
    env = dict(os.environ)
    env["AIASE_RESULT_PATH"] = str(result_path)
    subprocess.run(
        [sys.executable, str(RUNNER), json.dumps(payload)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result_path.read_text(encoding="utf-8"))


def test_open_track_sql_a_error_preserves_sql_b_result():
    result = run_open_track(
        {
            "task_id": "diff_err",
            "db_schema": "CREATE TABLE orders (id INT, status TEXT);",
            "db_seed": "INSERT INTO orders VALUES (1, 'paid');",
            "sql_a": "SELECT nonexistent_col FROM orders",
            "sql_b": "SELECT id FROM orders",
        }
    )

    assert result["task_id"] == "diff_err"
    assert result["equivalent"] is False
    assert result["error"].startswith("sql_a_error:")
    assert result["diff_type"] == "sql_error"
    assert result["confidence"] == 0.0
    assert result["columns_a"] == []
    assert result["columns_b"] == ["id"]
    assert result["row_count_a"] == 0
    assert result["row_count_b"] == 1


def test_open_track_sql_b_error_preserves_sql_a_result():
    result = run_open_track(
        {
            "task_id": "diff_b_err",
            "db_schema": "CREATE TABLE orders (id INT, status TEXT);",
            "db_seed": "INSERT INTO orders VALUES (1, 'paid');",
            "sql_a": "SELECT id FROM orders",
            "sql_b": "SELECT nonexistent_col FROM orders",
        }
    )

    assert result["task_id"] == "diff_b_err"
    assert result["equivalent"] is False
    assert result["error"].startswith("sql_b_error:")
    assert result["diff_type"] == "sql_error"
    assert result["confidence"] == 0.0
    assert result["columns_a"] == ["id"]
    assert result["columns_b"] == []
    assert result["row_count_a"] == 1
    assert result["row_count_b"] == 0


def test_open_track_missing_payload_is_reported_before_sql_execution():
    result = run_open_track(
        {
            "task_id": "diff_missing",
            "db_schema": "CREATE TABLE orders (id INT);",
            "db_seed": "",
            "sql_a": "SELECT id FROM orders",
        }
    )

    assert result["task_id"] == "diff_missing"
    assert result["equivalent"] is False
    assert result["error"] == "missing_input: sql_b"
    assert result["diff_type"] == "input_error"
    assert result["confidence"] == 0.0
    assert result["columns_a"] == []
    assert result["columns_b"] == []


def test_open_track_normalizes_integral_float_values():
    result = run_open_track(
        {
            "task_id": "diff_numeric",
            "db_schema": "CREATE TABLE values_a (x REAL); CREATE TABLE values_b (x INT);",
            "db_seed": "INSERT INTO values_a VALUES (1.0); INSERT INTO values_b VALUES (1);",
            "sql_a": "SELECT x AS id FROM values_a",
            "sql_b": "SELECT x AS id FROM values_b",
        }
    )

    assert result["equivalent"] is True
    assert result["diff_type"] == "equivalent"
    assert result["rows_only_in_a"] == []
    assert result["rows_only_in_b"] == []


def test_open_track_counts_duplicate_rows_as_multiset():
    result = run_open_track(
        {
            "task_id": "diff_multiset",
            "db_schema": "CREATE TABLE t (id INT);",
            "db_seed": "INSERT INTO t VALUES (1), (1), (2);",
            "sql_a": "SELECT id FROM t",
            "sql_b": "SELECT id FROM t WHERE rowid IN (1, 3)",
        }
    )

    assert result["equivalent"] is False
    assert result["diff_type"] == "row_multiset_mismatch"
    assert result["rows_only_in_a"] == [{"id": 1}]
    assert result["rows_only_in_b"] == []
    assert result["rows_only_in_a_total"] == 1
    assert result["rows_only_in_b_total"] == 0
    assert result["diff_rows_truncated"] is False
    assert result["witness"] == {
        "type": "row_only_in_a",
        "side": "sql_a",
        "row": {"id": 1},
    }
    assert result["execution_mode"] == "isolated_read_only"
    assert result["value_normalization"]["integral_float_as_int"] is True


def test_open_track_truncates_large_diff_rows():
    values = ", ".join(f"({index})" for index in range(150))
    result = run_open_track(
        {
            "task_id": "diff_large",
            "db_schema": "CREATE TABLE t (id INT);",
            "db_seed": f"INSERT INTO t VALUES {values};",
            "sql_a": "SELECT id FROM t",
            "sql_b": "SELECT id FROM t WHERE 0",
        }
    )

    assert result["equivalent"] is False
    assert len(result["rows_only_in_a"]) == 100
    assert result["rows_only_in_b"] == []
    assert result["rows_only_in_a_total"] == 150
    assert result["rows_only_in_b_total"] == 0
    assert result["diff_rows_truncated"] is True
    assert "150 rows appear only in sql_a" in result["rationale"]
    assert "rows_only_in_a showing first 100 of 150" in result["rationale"]


def test_open_track_isolates_side_effecting_sql():
    result = run_open_track(
        {
            "task_id": "diff_side_effect",
            "db_schema": "CREATE TABLE t (id INT);",
            "db_seed": "INSERT INTO t VALUES (1), (2);",
            "sql_a": "DELETE FROM t",
            "sql_b": "SELECT id FROM t",
        }
    )

    assert result["equivalent"] is False
    assert result["diff_type"] == "sql_error"
    assert result["error"].startswith("sql_a_error:")
    assert result["columns_b"] == ["id"]
    assert result["row_count_b"] == 2


def test_open_track_handles_blob_values():
    result = run_open_track(
        {
            "task_id": "diff_blob",
            "db_schema": "CREATE TABLE t (payload BLOB);",
            "db_seed": "INSERT INTO t VALUES (x'0A0B'), (x'0A0C');",
            "sql_a": "SELECT payload FROM t",
            "sql_b": "SELECT payload FROM t WHERE payload = x'0A0B'",
        }
    )

    assert result["equivalent"] is False
    assert result["rows_only_in_a"] == [{"payload": {"__blob_hex__": "0a0c"}}]


def test_open_track_preserves_duplicate_column_positions():
    result = run_open_track(
        {
            "task_id": "diff_duplicate_columns",
            "db_schema": "CREATE TABLE t (id INT, other INT);",
            "db_seed": "INSERT INTO t VALUES (1, 2);",
            "sql_a": "SELECT id, other AS id FROM t",
            "sql_b": "SELECT id, id FROM t",
        }
    )

    assert result["equivalent"] is False
    assert result["columns_a"] == ["id", "id"]
    assert result["columns_b"] == ["id", "id"]
    assert result["rows_only_in_a"] == [{"id#1": 1, "id#2": 2}]
    assert result["rows_only_in_b"] == [{"id#1": 1, "id#2": 1}]
    assert result["witness"] == {
        "type": "row_only_in_a",
        "side": "sql_a",
        "row": {"id#1": 1, "id#2": 2},
    }


def test_open_track_column_mismatch_witness():
    result = run_open_track(
        {
            "task_id": "diff_column_witness",
            "db_schema": "CREATE TABLE users (id INT, name TEXT);",
            "db_seed": "INSERT INTO users VALUES (1, 'Ada');",
            "sql_a": "SELECT id, name FROM users",
            "sql_b": "SELECT id FROM users",
        }
    )

    assert result["equivalent"] is False
    assert result["diff_type"] == "column_mismatch"
    assert result["witness"] == {
        "type": "column_mismatch",
        "columns_a": ["id", "name"],
        "columns_b": ["id"],
    }


def test_open_track_times_out_expensive_queries():
    result = run_open_track(
        {
            "task_id": "diff_timeout",
            "db_schema": "CREATE TABLE t (id INT);",
            "db_seed": "",
            "sql_a": (
                "WITH RECURSIVE cnt(x) AS ("
                "SELECT 1 UNION ALL SELECT x + 1 FROM cnt WHERE x < 100000000"
                ") SELECT sum(x) FROM cnt"
            ),
            "sql_b": "SELECT id FROM t",
        }
    )

    assert result["equivalent"] is False
    assert result["diff_type"] == "sql_timeout"
    assert result["error"].startswith("sql_a_timeout:")
    assert result["columns_b"] == ["id"]
    assert result["witness"]["type"] == "sql_timeout"
