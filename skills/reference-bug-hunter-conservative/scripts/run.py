#!/usr/bin/env python3
"""reference-bug-hunter-conservative — low-FP probe-based bug reporter."""

from __future__ import annotations

import json
import signal
import sys
import traceback
from contextlib import contextmanager
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TASK_DIR = REPO_ROOT / "dev_set" / "pairwise" / "reference_tasks"


class _Timeout(Exception):
    pass


@contextmanager
def _time_limit(sec: float):
    if not hasattr(signal, "SIGALRM"):
        yield
        return
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


def _probe_for_crashes(code: str, entry: str, test_cases: list[dict], timeout: float = 1.0) -> list[int]:
    """Return sorted unique crash line numbers (in <candidate>)."""
    ns: dict = {}
    try:
        exec(compile(code, "<candidate>", "exec"), ns)
    except Exception as e:
        # whole-module compile/exec failure → can't probe
        tb = traceback.extract_tb(e.__traceback__)
        for f in tb:
            if f.filename == "<candidate>" and f.lineno:
                return [f.lineno]
        return [1]
    fn = ns.get(entry)
    if not callable(fn):
        return []
    crash_lines: set[int] = set()
    for tc in test_cases:
        args = tc.get("input", [])
        try:
            with _time_limit(timeout):
                _ = fn(*args) if isinstance(args, list) else fn(args)
        except _Timeout:
            continue
        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            for f in tb:
                if f.filename == "<candidate>" and f.lineno:
                    crash_lines.add(f.lineno)
    return sorted(crash_lines)


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
        return emit({"task_id": task_id, "verdict": "clean", "bugs": [], "confidence": 0.5})

    entry = task["constraints"]["entry_function"]
    crashes = _probe_for_crashes(code, entry, task.get("test_cases", []))

    if not crashes:
        return emit({"task_id": task_id, "verdict": "clean", "bugs": [], "confidence": 0.8})

    bug = {
        "line_start": crashes[0],
        "line_end": crashes[0],
        "severity": "medium",
        "type": "edge_case",
        "description": f"A reference test case crashed at line {crashes[0]}; unhandled edge condition.",
        "suggested_fix": "Add explicit guards for empty input / boundary values; verify against the task's edge spec.",
    }
    return emit({
        "task_id": task_id,
        "verdict": "buggy",
        "bugs": [bug],
        "confidence": 0.85,
    })


if __name__ == "__main__":
    sys.exit(main(sys.argv))
