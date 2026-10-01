#!/usr/bin/env python3
"""reference-bug-hunter-noisy — conservative + seeded perturbation."""

from __future__ import annotations

import ast
import hashlib
import json
import random
import signal
import sys
import traceback
from contextlib import contextmanager
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TASK_DIR = REPO_ROOT / "dev_set" / "pairwise" / "reference_tasks"

FIXED_SEED = 20260601  # audit-friendly constant; see BEHAVIOR.md
DROP_P = 0.30
INJECT_P = 0.30
MAX_BUGS = 3


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


def _conservative_crashes(code: str, entry: str, test_cases: list[dict]) -> list[int]:
    ns: dict = {}
    try:
        exec(compile(code, "<candidate>", "exec"), ns)
    except Exception as e:
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
            with _time_limit(1.0):
                _ = fn(*args) if isinstance(args, list) else fn(args)
        except _Timeout:
            continue
        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__)
            for f in tb:
                if f.filename == "<candidate>" and f.lineno:
                    crash_lines.add(f.lineno)
                    break
    return sorted(crash_lines)


def _seed_for(task_id: str, code: str) -> int:
    h = hashlib.sha256(f"{task_id}|{code}".encode("utf-8")).hexdigest()
    return FIXED_SEED ^ int(h[:8], 16)


def _candidate_lines(code: str) -> list[int]:
    """Lines that are non-empty + non-comment (candidates for fake injection)."""
    out: list[int] = []
    for i, line in enumerate(code.splitlines(), start=1):
        s = line.strip()
        if s and not s.startswith("#"):
            out.append(i)
    return out


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
    real = _conservative_crashes(code, entry, task.get("test_cases", []))

    rng = random.Random(_seed_for(task_id, code))

    kept: list[dict] = []
    for ln in real:
        if rng.random() >= DROP_P:
            kept.append({
                "line_start": ln, "line_end": ln,
                "severity": "medium", "type": "edge_case",
                "description": f"Probe crash at line {ln}.",
                "suggested_fix": "Investigate edge handling here.",
            })

    cand = [n for n in _candidate_lines(code) if n not in real]
    rng.shuffle(cand)
    for ln in cand:
        if len(kept) >= MAX_BUGS:
            break
        if rng.random() < INJECT_P:
            kept.append({
                "line_start": ln, "line_end": ln,
                "severity": "low", "type": "logic_error",
                "description": "Suspicious pattern (auto-injected by noisy reference).",
                "suggested_fix": "Manually review.",
                "_synthetic": True,
            })

    if not kept:
        return emit({"task_id": task_id, "verdict": "clean", "bugs": [], "confidence": 0.4})
    return emit({
        "task_id": task_id,
        "verdict": "buggy",
        "bugs": kept[:MAX_BUGS],
        "confidence": 0.5,
    })


if __name__ == "__main__":
    sys.exit(main(sys.argv))
