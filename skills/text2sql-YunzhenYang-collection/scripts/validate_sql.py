#!/usr/bin/env python3
"""
Deterministic SQL validator for text2sql skill.

Usage:
    python validate_sql.py '{"schema_ddl":"CREATE TABLE ...", "sql":"SELECT ..."}'

The schema key may be either `schema_ddl` or `db_schema`. The latter matches
the task payload field name used by the grader and is accepted defensively.

Prints a single fenced JSON block:
    {"ok": true|false, "error": "<sqlite error or rule violation>", "error_code": "<category>"}

Strategy:
1. Reject multiple statements / DDL / DML up front (cheap, no DB needed).
2. Build the schema in an in-memory sqlite (no data).
3. Run `EXPLAIN <sql>` — this parses & resolves column names without needing data.
4. On sqlite3.Error, return a normalized category plus the original detail so
   the LLM can fix the draft with a targeted repair.
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys


FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|ATTACH|DETACH|REPLACE|TRUNCATE|VACUUM|PRAGMA)\b",
    re.IGNORECASE,
)


def _emit(ok: bool, error: str = "", error_code: str = "") -> int:
    out = {"ok": bool(ok), "error": error, "error_code": error_code}
    sys.stdout.write("```json\n")
    sys.stdout.write(json.dumps(out, ensure_ascii=False))
    sys.stdout.write("\n```\n")
    return 0 if ok else 1


def _classify_sqlite_error(error: sqlite3.Error) -> str:
    message = str(error).lower()
    if "no such column" in message:
        return "unknown_column"
    if "no such table" in message:
        return "unknown_table"
    if "syntax error" in message or "incomplete input" in message:
        return "syntax_error"
    return "sqlite_error"


def _format_error(error_code: str, detail: str) -> str:
    return f"{error_code}: {detail}"


def validate_detail(schema_ddl: str, sql: str) -> tuple[bool, str, str]:
    sql_stripped = sql.strip().rstrip(";")
    if not sql_stripped:
        return False, _format_error("empty_sql", "empty SQL"), "empty_sql"
    if ";" in sql_stripped:
        return False, _format_error("multiple_statements", "multiple SQL statements not allowed"), "multiple_statements"
    if FORBIDDEN.search(sql_stripped):
        return False, _format_error("forbidden_statement", "DDL/DML/PRAGMA not allowed; SELECT only"), "forbidden_statement"

    con = sqlite3.connect(":memory:")
    try:
        if schema_ddl:
            try:
                con.executescript(schema_ddl)
            except sqlite3.Error as e:
                return False, _format_error("schema_error", f"schema DDL did not parse: {e}"), "schema_error"
        try:
            con.execute(f"EXPLAIN {sql_stripped}")
        except sqlite3.Error as e:
            error_code = _classify_sqlite_error(e)
            return False, _format_error(error_code, f"SQL did not compile: {e}"), error_code
        return True, "", ""
    finally:
        con.close()


def validate(schema_ddl: str, sql: str) -> tuple[bool, str]:
    ok, error, _error_code = validate_detail(schema_ddl, sql)
    return ok, error


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        return _emit(False, "usage_error: usage: validate_sql.py '<json payload>'", "usage_error")
    try:
        payload = json.loads(argv[1])
    except json.JSONDecodeError as e:
        return _emit(False, f"invalid_json: argv JSON invalid: {e}", "invalid_json")
    schema_ddl = str(payload.get("schema_ddl", "") or payload.get("db_schema", ""))
    sql = str(payload.get("sql", ""))
    ok, err, error_code = validate_detail(schema_ddl, sql)
    return _emit(ok, err, error_code)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
