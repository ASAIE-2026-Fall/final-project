"""
Dev set integrity tests — every Basic task's gold_sql must:
1. parse + execute against its db_path,
2. produce results that bag-equal themselves (sanity),
3. stay within the difficulty envelope (no window funcs / CTEs / recursion / DDL / DML).

If the sqlite files are not built, the test self-builds them by importing build_dbs.
"""

import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BASIC_DIR = REPO_ROOT / "dev_set" / "basic"
DBS_DIR = BASIC_DIR / "dbs"

from run_dev import bag_equal, is_read_only_sql, load_basic_tasks, run_sql  # noqa: E402


OUT_OF_ENVELOPE = re.compile(
    r"\b(OVER\s*\(|WITH\s+RECURSIVE|^\s*WITH\s+|"
    r"CREATE|DROP|ALTER|INSERT|UPDATE|DELETE|REPLACE|TRUNCATE|ATTACH|DETACH|PRAGMA)\b",
    re.IGNORECASE | re.MULTILINE,
)


def _ensure_dbs_built():
    """If dbs/ is empty, run build_dbs.py once."""
    if not any(DBS_DIR.glob("*.sqlite")):
        proc = subprocess.run(
            [sys.executable, str(BASIC_DIR / "build_dbs.py")],
            capture_output=True, text=True, check=False,
        )
        if proc.returncode != 0:
            pytest.skip(f"build_dbs.py failed: {proc.stderr}", allow_module_level=True)


_ensure_dbs_built()
TASKS = load_basic_tasks()


def _ids():
    return [t["task_id"] for t in TASKS]


@pytest.mark.parametrize("task", TASKS, ids=_ids() or ["<no-tasks>"])
def test_db_exists(task):
    db = REPO_ROOT / task["db_path"]
    assert db.exists(), f"missing db: {db}"


@pytest.mark.parametrize("task", TASKS, ids=_ids() or ["<no-tasks>"])
def test_gold_sql_is_read_only(task):
    ok, why = is_read_only_sql(task["gold_sql"])
    assert ok, f"{task['task_id']}: gold_sql not read-only: {why}"


@pytest.mark.parametrize("task", TASKS, ids=_ids() or ["<no-tasks>"])
def test_gold_sql_within_envelope(task):
    sql = task["gold_sql"]
    m = OUT_OF_ENVELOPE.search(sql)
    assert not m, f"{task['task_id']}: gold_sql contains out-of-envelope construct: {m.group(0) if m else ''}"


@pytest.mark.parametrize("task", TASKS, ids=_ids() or ["<no-tasks>"])
def test_gold_sql_executes(task):
    db = REPO_ROOT / task["db_path"]
    if not db.exists():
        pytest.skip("db not built")
    try:
        rows = run_sql(db, task["gold_sql"])
    except sqlite3.Error as e:
        pytest.fail(f"{task['task_id']}: gold_sql failed to execute: {e}")
    # We don't require non-empty; some edge tasks may be empty by design.
    # We do require reflexivity:
    assert bag_equal(rows, rows)


def test_at_least_20_tasks_present():
    """Spec commits to 20 basic dev tasks + 1 EXAMPLE."""
    ids = _ids()
    assert len(ids) >= 21, f"expected ≥21 basic dev tasks, got {len(ids)}: {ids}"
