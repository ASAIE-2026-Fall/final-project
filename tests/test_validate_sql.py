"""Tests for skills/text2sql-YunzhenYang-collection/scripts/validate_sql.py."""

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VS_PATH = REPO_ROOT / "skills" / "text2sql-YunzhenYang-collection" / "scripts" / "validate_sql.py"


def _load():
    spec = importlib.util.spec_from_file_location("validate_sql", VS_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


vs = _load()

SCHEMA = """
CREATE TABLE Students (sid INTEGER PRIMARY KEY, name TEXT, dept TEXT);
CREATE TABLE Courses (cid INTEGER PRIMARY KEY, title TEXT, professor TEXT, year INTEGER);
CREATE TABLE Enrollments (sid INTEGER, cid INTEGER, score INTEGER, PRIMARY KEY (sid, cid));
"""


def test_valid_select_passes():
    ok, err = vs.validate(SCHEMA, "SELECT name FROM Students WHERE dept = 'CS';")
    assert ok, err


def test_nonexistent_column_fails():
    ok, err = vs.validate(SCHEMA, "SELECT nonexistent FROM Students;")
    assert not ok
    assert "nonexistent" in err.lower() or "no such column" in err.lower()


def test_nonexistent_table_fails():
    ok, err = vs.validate(SCHEMA, "SELECT 1 FROM NoSuchTable;")
    assert not ok


def test_syntax_error_fails():
    ok, err = vs.validate(SCHEMA, "SELECT FROM WHERE;")
    assert not ok


def test_empty_sql_fails():
    ok, err = vs.validate(SCHEMA, "")
    assert not ok


def test_ddl_rejected():
    ok, err = vs.validate(SCHEMA, "CREATE TABLE X (id INTEGER);")
    assert not ok
    assert "DDL" in err or "DML" in err


def test_dml_rejected():
    for stmt in ("INSERT INTO Students VALUES (99, 'x', 'CS')",
                 "UPDATE Students SET name = 'y' WHERE sid = 1",
                 "DELETE FROM Students"):
        ok, err = vs.validate(SCHEMA, stmt)
        assert not ok, f"should reject: {stmt}"


def test_multiple_statements_rejected():
    ok, err = vs.validate(SCHEMA, "SELECT 1; SELECT 2")
    assert not ok


def test_trailing_semicolon_ok():
    ok, err = vs.validate(SCHEMA, "SELECT 1 FROM Students;")
    assert ok, err


def test_join_passes():
    sql = (
        "SELECT s.name FROM Students s "
        "JOIN Enrollments e ON s.sid = e.sid "
        "JOIN Courses c ON e.cid = c.cid "
        "WHERE c.title = 'AI Foundations'"
    )
    ok, err = vs.validate(SCHEMA, sql)
    assert ok, err


def test_main_accepts_db_schema_payload_key(capsys):
    rc = vs.main([
        "validate_sql.py",
        json.dumps({"db_schema": SCHEMA, "sql": "SELECT name FROM Students;"})
    ])
    captured = capsys.readouterr().out
    assert rc == 0
    assert '"ok": true' in captured


def test_validate_detail_returns_normalized_error_codes():
    cases = [
        ("SELECT nonexistent FROM Students;", "unknown_column"),
        ("SELECT 1 FROM NoSuchTable;", "unknown_table"),
        ("SELECT FROM WHERE;", "syntax_error"),
        ("", "empty_sql"),
        ("SELECT 1; SELECT 2", "multiple_statements"),
        ("DELETE FROM Students", "forbidden_statement"),
    ]

    for sql, expected_code in cases:
        ok, err, code = vs.validate_detail(SCHEMA, sql)
        assert not ok
        assert code == expected_code
        assert err.startswith(f"{expected_code}:")


def test_schema_parse_error_is_normalized():
    ok, err, code = vs.validate_detail("CREATE TABLE broken (", "SELECT 1")
    assert not ok
    assert code == "schema_error"
    assert err.startswith("schema_error:")


def test_main_emits_error_code(capsys):
    rc = vs.main([
        "validate_sql.py",
        json.dumps({"db_schema": SCHEMA, "sql": "SELECT nonexistent FROM Students;"})
    ])
    captured = capsys.readouterr().out
    assert rc == 1
    assert '"ok": false' in captured
    assert '"error_code": "unknown_column"' in captured
