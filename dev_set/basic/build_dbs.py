#!/usr/bin/env python3
"""
Build all `dev_set/basic/dbs/task_nl2sql_XXX.sqlite` files from in-source schema +
data definitions.

Run:
    python dev_set/basic/build_dbs.py

Idempotent — deletes and rebuilds each .sqlite. The 20 Basic tasks are grouped
into 5 schemas (university, ecommerce, library, sports, hospital); within each
schema, tasks share the same data, so we generate one canonical DB per schema
and copy it out to <task_id>.sqlite paths.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import sys
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
DBS_DIR = THIS_DIR / "dbs"
DBS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Schemas + data — kept compact but with enough rows for gold_sql to be non-trivial.
# ---------------------------------------------------------------------------

UNIVERSITY = {
    "ddl": """
    CREATE TABLE Students (sid INTEGER PRIMARY KEY, name TEXT NOT NULL, dept TEXT NOT NULL);
    CREATE TABLE Courses  (cid INTEGER PRIMARY KEY, title TEXT NOT NULL, professor TEXT NOT NULL, year INTEGER NOT NULL);
    CREATE TABLE Enrollments (sid INTEGER NOT NULL, cid INTEGER NOT NULL, score INTEGER NOT NULL,
                              PRIMARY KEY (sid, cid));
    """,
    "data": [
        ("Students", [
            (1, "Alice", "CS"), (2, "Bob", "EE"), (3, "Chen", "CS"),
            (4, "Diana", "Math"), (5, "Eli", "CS"), (6, "Fang", "EE"),
        ]),
        ("Courses", [
            (101, "AI Foundations",   "Wang",  2025),
            (102, "Linear Algebra",   "Lin",   2025),
            (103, "Operating Systems","Wang",  2024),
            (104, "Networks",         "Tsai",  2025),
            (105, "Calculus",         "Lin",   2024),
        ]),
        ("Enrollments", [
            (1, 101, 92), (1, 102, 88), (1, 105, 91),
            (2, 101, 75), (2, 104, 80),
            (3, 101, 95), (3, 103, 70), (3, 104, 85),
            (4, 102, 99), (4, 105, 89),
            (5, 101, 60),
            (6, 104, 91), (6, 103, 88), (6, 105, 72),
        ]),
    ],
}

ECOMMERCE = {
    "ddl": """
    CREATE TABLE Customers (cid INTEGER PRIMARY KEY, name TEXT NOT NULL, country TEXT NOT NULL);
    CREATE TABLE Products  (pid INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL, price REAL NOT NULL);
    CREATE TABLE Orders    (oid INTEGER PRIMARY KEY, cid INTEGER NOT NULL, ts TEXT NOT NULL);
    CREATE TABLE OrderItems(oid INTEGER NOT NULL, pid INTEGER NOT NULL, qty INTEGER NOT NULL,
                            PRIMARY KEY (oid, pid));
    """,
    "data": [
        ("Customers", [
            (1, "Alice",  "TW"), (2, "Bob",   "US"), (3, "Chen", "TW"),
            (4, "Diana",  "JP"), (5, "Eli",   "US"), (6, "Fang", "TW"),
        ]),
        ("Products", [
            (10, "Phone",   "Electronics", 600.0),
            (11, "Laptop",  "Electronics", 1200.0),
            (12, "Novel",   "Books",       15.0),
            (13, "Cookbook","Books",       25.0),
            (14, "Mug",     "Home",        8.0),
        ]),
        ("Orders", [
            (1001, 1, "2025-03-01"), (1002, 1, "2025-03-15"),
            (1003, 2, "2025-04-02"),
            (1004, 3, "2025-04-10"), (1005, 3, "2025-05-05"),
            (1006, 4, "2025-05-12"),
            # customer 5 (Eli) has no orders — for LEFT JOIN test
        ]),
        ("OrderItems", [
            (1001, 10, 1), (1001, 12, 2),
            (1002, 14, 4),
            (1003, 11, 1), (1003, 13, 1),
            (1004, 10, 2),
            (1005, 12, 3), (1005, 13, 1),
            (1006, 11, 1),
        ]),
    ],
}

LIBRARY = {
    "ddl": """
    CREATE TABLE Books       (bid INTEGER PRIMARY KEY, title TEXT NOT NULL);
    CREATE TABLE Authors     (aid INTEGER PRIMARY KEY, name TEXT NOT NULL);
    CREATE TABLE BookAuthors (bid INTEGER NOT NULL, aid INTEGER NOT NULL, PRIMARY KEY (bid, aid));
    CREATE TABLE Members     (mid INTEGER PRIMARY KEY, name TEXT NOT NULL, joined TEXT NOT NULL);
    CREATE TABLE Loans       (lid INTEGER PRIMARY KEY, bid INTEGER NOT NULL, mid INTEGER NOT NULL,
                              due_date TEXT NOT NULL, returned INTEGER NOT NULL);
    """,
    "data": [
        ("Books", [
            (1, "The Dispossessed"),
            (2, "A Wizard of Earthsea"),
            (3, "Foundation"),
            (4, "Project Hail Mary"),
            (5, "Babel"),
        ]),
        ("Authors", [
            (10, "Le Guin"), (11, "Asimov"), (12, "Weir"), (13, "Kuang"),
        ]),
        ("BookAuthors", [
            (1, 10), (2, 10),  # Le Guin → 2 books
            (3, 11),
            (4, 12),
            (5, 13),
        ]),
        ("Members", [
            (100, "Alice", "2024-01-10"), (101, "Bob", "2024-03-22"),
            (102, "Chen",  "2025-02-15"), (103, "Diana", "2025-04-01"),
        ]),
        ("Loans", [
            (1000, 1, 100, "2025-05-01", 1),
            (1001, 2, 100, "2025-05-20", 1),
            (1002, 3, 101, "2025-06-01", 0),  # not returned
            (1003, 4, 102, "2025-05-15", 1),
            (1004, 5, 103, "2025-06-10", 0),  # not returned
            (1005, 3, 100, "2025-06-30", 0),  # not returned
        ]),
    ],
}

SPORTS = {
    "ddl": """
    CREATE TABLE Teams   (tid INTEGER PRIMARY KEY, name TEXT NOT NULL, city TEXT NOT NULL);
    CREATE TABLE Players (pid INTEGER PRIMARY KEY, name TEXT NOT NULL, tid INTEGER NOT NULL, position TEXT NOT NULL);
    CREATE TABLE Games   (gid INTEGER PRIMARY KEY, home_tid INTEGER NOT NULL, away_tid INTEGER NOT NULL, date TEXT NOT NULL);
    CREATE TABLE Goals   (gid INTEGER NOT NULL, pid INTEGER NOT NULL, minute INTEGER NOT NULL);
    """,
    "data": [
        ("Teams", [
            (1, "Tigers", "Taipei"), (2, "Dragons", "Tainan"),
            (3, "Eagles", "Taichung"), (4, "Sharks", "Kaohsiung"),
        ]),
        ("Players", [
            (1, "Aaron", 1, "FW"), (2, "Brian", 1, "MF"), (3, "Carl",  1, "DF"),
            (4, "David", 2, "FW"), (5, "Erin",  2, "MF"),
            (6, "Frank", 3, "FW"), (7, "Gina",  3, "DF"),
            (8, "Hank",  4, "FW"),
        ]),
        ("Games", [
            (1, 1, 2, "2025-03-01"), (2, 1, 3, "2025-03-08"),
            (3, 2, 1, "2025-03-15"), (4, 3, 4, "2025-03-22"),
            (5, 1, 4, "2025-04-01"), (6, 4, 2, "2025-04-05"),
        ]),
        ("Goals", [
            (1, 1, 15), (1, 1, 70), (1, 4, 33),
            (2, 1, 22), (2, 6, 50),
            (3, 4, 11), (3, 4, 60),
            (4, 6, 18), (4, 8, 80),
            (5, 1, 5), (5, 1, 27), (5, 2, 88),
            (6, 8, 12),
        ]),
    ],
}

HOSPITAL = {
    "ddl": """
    CREATE TABLE Departments  (did INTEGER PRIMARY KEY, name TEXT NOT NULL);
    CREATE TABLE Doctors      (doc_id INTEGER PRIMARY KEY, name TEXT NOT NULL, did INTEGER NOT NULL);
    CREATE TABLE Patients     (pid INTEGER PRIMARY KEY, name TEXT NOT NULL, age INTEGER NOT NULL);
    CREATE TABLE Appointments (aid INTEGER PRIMARY KEY, doc_id INTEGER NOT NULL, pid INTEGER NOT NULL,
                               date TEXT NOT NULL, status TEXT NOT NULL);
    """,
    "data": [
        ("Departments", [
            (1, "Cardiology"), (2, "Neurology"),
            (3, "Pediatrics"), (4, "Oncology"),
        ]),
        ("Doctors", [
            (10, "Dr. Wang", 1), (11, "Dr. Lin", 1),
            (12, "Dr. Tsai", 2),
            (13, "Dr. Chang", 3),
            (14, "Dr. Liu",  4), (15, "Dr. Huang", 4),
        ]),
        ("Patients", [
            (100, "Alice",   72), (101, "Bob",   65),
            (102, "Chen",     8), (103, "Diana", 35),
            (104, "Eli",     80), (105, "Fang",  45),
        ]),
        ("Appointments", [
            (1, 10, 100, "2025-04-01", "completed"),
            (2, 10, 101, "2025-04-02", "completed"),
            (3, 11, 100, "2025-04-15", "completed"),
            (4, 12, 103, "2025-04-20", "completed"),
            (5, 13, 102, "2025-05-01", "completed"),
            (6, 14, 104, "2025-05-05", "completed"),
            (7, 15, 105, "2025-05-12", "scheduled"),
            (8, 14, 100, "2025-05-20", "completed"),
        ]),
    ],
}


SCHEMAS = {
    "university": UNIVERSITY,
    "ecommerce":  ECOMMERCE,
    "library":    LIBRARY,
    "sports":     SPORTS,
    "hospital":   HOSPITAL,
}

# task_id → schema name. 20 tasks, 4 per schema.
TASK_TO_SCHEMA = {
    "task_nl2sql_001": "university",
    "task_nl2sql_002": "university",
    "task_nl2sql_003": "university",
    "task_nl2sql_004": "university",
    "task_nl2sql_005": "ecommerce",
    "task_nl2sql_006": "ecommerce",
    "task_nl2sql_007": "ecommerce",
    "task_nl2sql_008": "ecommerce",
    "task_nl2sql_009": "library",
    "task_nl2sql_010": "library",
    "task_nl2sql_011": "library",
    "task_nl2sql_012": "library",
    "task_nl2sql_013": "sports",
    "task_nl2sql_014": "sports",
    "task_nl2sql_015": "sports",
    "task_nl2sql_016": "sports",
    "task_nl2sql_017": "hospital",
    "task_nl2sql_018": "hospital",
    "task_nl2sql_019": "hospital",
    "task_nl2sql_020": "hospital",
    # Plus the EXAMPLE that was shipped pre-CL
    "task_nl2sql_EXAMPLE": "university",
}


def _build_one(schema_name: str) -> Path:
    """Materialize a temp sqlite for the given schema, return its path."""
    out = DBS_DIR / f"_{schema_name}.sqlite"
    if out.exists():
        out.unlink()
    con = sqlite3.connect(str(out))
    try:
        spec = SCHEMAS[schema_name]
        con.executescript(spec["ddl"])
        for table, rows in spec["data"]:
            placeholders = ",".join("?" * len(rows[0]))
            con.executemany(f"INSERT INTO {table} VALUES ({placeholders})", rows)
        con.commit()
    finally:
        con.close()
    return out


def main() -> int:
    print(f"[build_dbs] target dir: {DBS_DIR}")
    canonical = {name: _build_one(name) for name in SCHEMAS}
    print(f"[build_dbs] built canonical: {sorted(canonical)}")

    for task_id, schema_name in TASK_TO_SCHEMA.items():
        dst = DBS_DIR / f"{task_id}.sqlite"
        if dst.exists():
            dst.unlink()
        shutil.copyfile(canonical[schema_name], dst)
        print(f"[build_dbs] {task_id}.sqlite  (schema={schema_name})")

    # cleanup canonical temp files
    for p in canonical.values():
        try:
            p.unlink()
        except OSError:
            pass

    print(f"[build_dbs] done. {len(TASK_TO_SCHEMA)} task DBs in {DBS_DIR.relative_to(THIS_DIR.parent.parent)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
