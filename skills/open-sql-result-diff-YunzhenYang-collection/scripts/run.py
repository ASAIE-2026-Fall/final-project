#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
import json
import os
import sqlite3
import sys
from typing import Any


_MAX_DIFF_ROWS = 100
_SQL_PROGRESS_STEP = 1000
_SQL_PROGRESS_LIMIT = 1000


def _resolve_result_path() -> str:
    return os.environ.get("AIASE_RESULT_PATH") or os.path.join(os.getcwd(), "aiase_result.json")


def _emit(result: dict[str, Any]) -> None:
    path = _resolve_result_path()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, sort_keys=True)
    try:
        os.replace(tmp, path)
    except PermissionError:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, sort_keys=True)
        try:
            os.remove(tmp)
        except OSError:
            pass
    print(f"written ok -> {path}")


def _load_payload() -> dict[str, Any]:
    # 優先從 stdin 讀（避免 shell quoting 問題）
    if not sys.stdin.isatty():
        raw = sys.stdin.read().strip()
        if raw:
            try:
                payload = json.loads(raw)
                return payload if isinstance(payload, dict) else {}
            except json.JSONDecodeError:
                return {}
    # fallback: argv
    if len(sys.argv) < 2:
        return {}
    try:
        payload = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _base_result(task_id: str) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "equivalent": False,
        "columns_a": [],
        "columns_b": [],
        "rows_only_in_a": [],
        "rows_only_in_b": [],
        "row_count_a": 0,
        "row_count_b": 0,
        "rationale": "",
        "error": "",
        "confidence": 1.0,
        "diff_type": "unknown",
        "rows_only_in_a_total": 0,
        "rows_only_in_b_total": 0,
        "diff_rows_truncated": False,
        "witness": None,
        "execution_mode": "isolated_read_only",
        "value_normalization": {
            "integral_float_as_int": True,
            "blob_encoding": "hex",
            "duplicate_column_suffix": "#<position>",
        },
    }


def _missing_fields(payload: dict[str, Any]) -> list[str]:
    missing = [field for field in ("task_id", "db_schema", "db_seed", "sql_a", "sql_b") if field not in payload]
    empty = [
        field
        for field in ("task_id", "db_schema", "sql_a", "sql_b")
        if field in payload and str(payload.get(field, "")).strip() == ""
    ]
    return missing + empty


def _clone_connection(source: sqlite3.Connection) -> sqlite3.Connection:
    target = sqlite3.connect(":memory:")
    source.backup(target)
    target.execute("PRAGMA query_only = ON")
    return target


def _run_sql(conn: sqlite3.Connection, sql: str) -> tuple[list[str], list[list[Any]]]:
    progress_calls = 0

    def _progress_handler() -> int:
        nonlocal progress_calls
        progress_calls += 1
        return 1 if progress_calls > _SQL_PROGRESS_LIMIT else 0

    conn.set_progress_handler(_progress_handler, _SQL_PROGRESS_STEP)
    try:
        cur = conn.execute(sql)
        columns = [str(desc[0]) for desc in (cur.description or [])]
        rows = [list(row) for row in cur.fetchall()]
    finally:
        conn.set_progress_handler(None, 0)

    return columns, rows


def _format_sql_error(label: str, exc: sqlite3.Error) -> str:
    if "interrupted" in str(exc).lower():
        return f"{label}_timeout: query exceeded progress limit"
    return f"{label}_error: {exc}"


def _display_column(column: str, index: int, columns: list[str]) -> str:
    if columns.count(column) == 1:
        return column
    return f"{column}#{index + 1}"


def _normalize_value(value: Any) -> Any:
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, bytes):
        return {"__blob_hex__": value.hex()}
    return value


def _canonical_value(value: Any) -> str:
    value = _normalize_value(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _row_key(row: list[Any], columns: list[str]) -> tuple[tuple[str, str, str], ...]:
    return tuple(
        (str(index), column, _canonical_value(row[index]))
        for index, column in enumerate(columns)
    )


def _key_to_row(key: tuple[tuple[str, str, str], ...], columns: list[str]) -> dict[str, Any]:
    return {
        _display_column(column, int(index), columns): json.loads(value)
        for index, column, value in key
    }


def _counter(rows: list[list[Any]], columns: list[str]) -> Counter[tuple[tuple[str, str, str], ...]]:
    return Counter(_row_key(row, columns) for row in rows)


def _expand(
    counter: Counter[tuple[tuple[str, str, str], ...]],
    columns: list[str],
    limit: int = _MAX_DIFF_ROWS,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in sorted(counter):
        remaining = limit - len(rows)
        if remaining <= 0:
            break
        rows.extend(_key_to_row(key, columns) for _ in range(min(counter[key], remaining)))
    return rows


def _truncation_note(total_a: int, total_b: int, shown_a: int, shown_b: int) -> str:
    notes: list[str] = []
    if shown_a < total_a:
        notes.append(f"rows_only_in_a showing first {shown_a} of {total_a}")
    if shown_b < total_b:
        notes.append(f"rows_only_in_b showing first {shown_b} of {total_b}")
    return f" ({'; '.join(notes)})" if notes else ""


def _row_witness(result: dict[str, Any]) -> dict[str, Any] | None:
    if result["rows_only_in_a"]:
        return {
            "type": "row_only_in_a",
            "side": "sql_a",
            "row": result["rows_only_in_a"][0],
        }
    if result["rows_only_in_b"]:
        return {
            "type": "row_only_in_b",
            "side": "sql_b",
            "row": result["rows_only_in_b"][0],
        }
    return None


def main() -> int:
    payload = _load_payload()
    task_id = str(payload.get("task_id", ""))
    result = _base_result(task_id)

    missing = _missing_fields(payload)
    if missing:
        result["error"] = f"missing_input: {', '.join(missing)}"
        result["confidence"] = 0.0
        result["diff_type"] = "input_error"
        result["rationale"] = f"Missing or empty required input field(s): {', '.join(missing)}."
        _emit(result)
        return 0

    db_schema = str(payload.get("db_schema", ""))
    db_seed = str(payload.get("db_seed", ""))
    sql_a = str(payload.get("sql_a", ""))
    sql_b = str(payload.get("sql_b", ""))

    try:
        conn = sqlite3.connect(":memory:")
        conn.executescript(db_schema)
    except sqlite3.Error as exc:
        result["error"] = f"schema_error: {exc}"
        result["confidence"] = 0.0
        result["diff_type"] = "schema_error"
        result["rationale"] = f"Schema setup failed: {exc}"
        _emit(result)
        return 0

    try:
        conn.executescript(db_seed)
    except sqlite3.Error as exc:
        result["error"] = f"seed_error: {exc}"
        result["confidence"] = 0.0
        result["diff_type"] = "seed_error"
        result["rationale"] = f"Seed data failed: {exc}"
        _emit(result)
        return 0

    columns_a: list[str] = []
    rows_a: list[list[Any]] = []
    columns_b: list[str] = []
    rows_b: list[list[Any]] = []
    sql_errors: list[str] = []

    conn_a = _clone_connection(conn)
    try:
        columns_a, rows_a = _run_sql(conn_a, sql_a)
        result["columns_a"] = columns_a
        result["row_count_a"] = len(rows_a)
    except sqlite3.Error as exc:
        sql_errors.append(_format_sql_error("sql_a", exc))
    finally:
        conn_a.close()

    conn_b = _clone_connection(conn)
    try:
        columns_b, rows_b = _run_sql(conn_b, sql_b)
        result["columns_b"] = columns_b
        result["row_count_b"] = len(rows_b)
    except sqlite3.Error as exc:
        sql_errors.append(_format_sql_error("sql_b", exc))
    finally:
        conn_b.close()

    if sql_errors:
        result["error"] = " | ".join(sql_errors)
        result["confidence"] = 0.0
        result["diff_type"] = "sql_timeout" if any("_timeout:" in error for error in sql_errors) else "sql_error"
        result["witness"] = {
            "type": result["diff_type"],
            "error": result["error"],
        }
        result["rationale"] = f"SQL execution failed: {'; '.join(sql_errors)}"
        _emit(result)
        return 0

    if columns_a != columns_b:
        result["diff_type"] = "column_mismatch"
        result["witness"] = {
            "type": "column_mismatch",
            "columns_a": columns_a,
            "columns_b": columns_b,
        }
        result["rationale"] = (
            f"Column mismatch: sql_a returns {columns_a}, sql_b returns {columns_b}."
        )
        _emit(result)
        return 0

    counter_a = _counter(rows_a, columns_a)
    counter_b = _counter(rows_b, columns_b)
    only_a = counter_a - counter_b
    only_b = counter_b - counter_a

    total_only_a = sum(only_a.values())
    total_only_b = sum(only_b.values())
    result["rows_only_in_a_total"] = total_only_a
    result["rows_only_in_b_total"] = total_only_b
    result["rows_only_in_a"] = _expand(only_a, columns_a)
    result["rows_only_in_b"] = _expand(only_b, columns_b)
    result["diff_rows_truncated"] = (
        len(result["rows_only_in_a"]) < total_only_a
        or len(result["rows_only_in_b"]) < total_only_b
    )
    result["equivalent"] = not only_a and not only_b

    if result["equivalent"]:
        result["diff_type"] = "equivalent"
        result["rationale"] = (
            "Result sets are equivalent: both return "
            f"{len(rows_a)} rows with identical column set."
        )
    else:
        result["diff_type"] = "row_multiset_mismatch"
        result["witness"] = _row_witness(result)
        result["rationale"] = (
            "Result sets differ: "
            f"{total_only_a} rows appear only in sql_a, "
            f"{total_only_b} rows appear only in sql_b"
            f"{_truncation_note(total_only_a, total_only_b, len(result['rows_only_in_a']), len(result['rows_only_in_b']))}."
        )

    _emit(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
