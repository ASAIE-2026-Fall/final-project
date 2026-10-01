#!/usr/bin/env python3
"""reference-bug-hunter-aggressive — high-recall probe + AST-smell reporter."""

from __future__ import annotations

import ast
import json
import signal
import sys
import traceback
from contextlib import contextmanager
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TASK_DIR = REPO_ROOT / "dev_set" / "pairwise" / "reference_tasks"

MAX_BUGS = 5


class _Timeout(Exception):
    pass


@contextmanager
def _time_limit(sec: float):
    if not hasattr(signal, "SIGALRM"):
        yield; return
    def _h(s, f): raise _Timeout("probe timed out")
    old = signal.signal(signal.SIGALRM, _h)
    signal.setitimer(signal.ITIMER_REAL, sec)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


def _load_task(task_id: str) -> dict | None:
    p = TASK_DIR / f"{task_id}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _run_probes(code: str, entry: str, test_cases: list[dict]) -> tuple[list[int], list[int]]:
    """Returns (crash_lines, mismatch_count)."""
    ns: dict = {}
    crash_lines: list[int] = []
    mismatch_count = 0
    try:
        exec(compile(code, "<candidate>", "exec"), ns)
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)
        for f in tb:
            if f.filename == "<candidate>" and f.lineno:
                return [f.lineno], 0
        return [1], 0
    fn = ns.get(entry)
    if not callable(fn):
        return [1], 0
    for tc in test_cases:
        args = tc.get("input", [])
        expected = tc.get("expected")
        try:
            with _time_limit(1.0):
                got = fn(*args) if isinstance(args, list) else fn(args)
        except _Timeout:
            crash_lines.append(1)
            continue
        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            for f in tb:
                if f.filename == "<candidate>" and f.lineno:
                    crash_lines.append(f.lineno)
                    break
            continue
        if got != expected:
            mismatch_count += 1
    return crash_lines, mismatch_count


def _ast_smells(code: str, entry: str) -> list[dict]:
    bugs: list[dict] = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return bugs
    entry_def_line = -1
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == entry:
                entry_def_line = node.lineno
            for d in node.args.defaults:
                if isinstance(d, (ast.List, ast.Dict, ast.Set)):
                    bugs.append({
                        "line_start": d.lineno, "line_end": d.lineno,
                        "severity": "low", "type": "api_misuse",
                        "description": "Mutable default argument; can persist state across calls.",
                        "suggested_fix": "Use None default and create the container inside the function.",
                    })
        elif isinstance(node, ast.ExceptHandler) and node.type is None:
            bugs.append({
                "line_start": node.lineno, "line_end": node.lineno,
                "severity": "low", "type": "unhandled_input",
                "description": "Bare `except:` swallows all exceptions including KeyboardInterrupt.",
                "suggested_fix": "Catch a specific exception type (e.g., `except ValueError:`).",
            })
        elif isinstance(node, ast.Call):
            f = node.func
            name = ""
            if isinstance(f, ast.Name):
                name = f.id
            elif isinstance(f, ast.Attribute):
                name = f.attr
            if name in ("eval", "exec"):
                bugs.append({
                    "line_start": node.lineno, "line_end": node.lineno,
                    "severity": "high", "type": "api_misuse",
                    "description": f"Use of `{name}` is unsafe with untrusted input.",
                    "suggested_fix": "Replace with a safe parser or explicit dispatch.",
                })
    return bugs


def emit(obj: dict) -> int:
    sys.stdout.write("```json\n")
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, indent=2))
    sys.stdout.write("\n```\n")
    return 0


def main(argv: list[str]) -> int:
    raw = argv[1] if len(argv) > 1 else "{}"
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        payload = {}

    task_id = str(payload.get("task_id", ""))
    code = str(payload.get("code", ""))
    task = _load_task(task_id)
    if task is None or not code:
        return emit({"task_id": task_id, "verdict": "clean", "bugs": [], "confidence": 0.4})

    entry = task["constraints"]["entry_function"]
    crashes, mismatches = _run_probes(code, entry, task.get("test_cases", []))

    bugs: list[dict] = []
    # crash lines first
    for ln in sorted(set(crashes)):
        bugs.append({
            "line_start": ln, "line_end": ln,
            "severity": "high", "type": "edge_case",
            "description": "A reference test case crashed here.",
            "suggested_fix": "Add explicit input/edge handling.",
        })
    if mismatches > 0:
        # find entry def line
        ln = 1
        try:
            for n in ast.walk(ast.parse(code)):
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == entry:
                    ln = n.lineno
                    break
        except SyntaxError:
            pass
        bugs.append({
            "line_start": ln, "line_end": ln,
            "severity": "high", "type": "logic_error",
            "description": f"{mismatches} reference cases returned wrong values; algorithm likely off.",
            "suggested_fix": "Re-derive the algorithm; verify against the task spec.",
        })
    bugs.extend(_ast_smells(code, entry))

    # dedupe (line_start, type)
    seen: set[tuple[int, str]] = set()
    unique: list[dict] = []
    for b in bugs:
        key = (b["line_start"], b["type"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(b)
    bugs = unique[:MAX_BUGS]

    if not bugs:
        return emit({"task_id": task_id, "verdict": "clean", "bugs": [], "confidence": 0.6})
    return emit({"task_id": task_id, "verdict": "buggy", "bugs": bugs, "confidence": 0.7})


if __name__ == "__main__":
    sys.exit(main(sys.argv))
