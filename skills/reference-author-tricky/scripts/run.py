#!/usr/bin/env python3
"""reference-author-tricky — emits canonical TRICKY (subtle-bug) code for the requested task."""

from __future__ import annotations

import json
import sys
from pathlib import Path

VARIANT = "tricky_code"

REPO_ROOT = Path(__file__).resolve().parents[3]
TASK_DIR = REPO_ROOT / "dev_set" / "pairwise" / "reference_tasks"

_STUB_TEMPLATE = "def {entry}(*args, **kwargs):\n    return None\n"


def _load_task(task_id: str) -> dict | None:
    p = TASK_DIR / f"{task_id}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _sloc(code: str) -> int:
    n = 0
    for line in code.splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            n += 1
    return n


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
    constraints = payload.get("constraints", {}) or {}
    entry = str(constraints.get("entry_function", "f"))

    task = _load_task(task_id)
    if task is None:
        code = _STUB_TEMPLATE.format(entry=entry)
        confidence = 0.0
        rationale = f"unknown task_id={task_id!r}; emitting degenerate stub"
    else:
        code = task.get(VARIANT, "")
        if not code:
            code = _STUB_TEMPLATE.format(entry=task.get("constraints", {}).get("entry_function", entry))
            confidence = 0.0
            rationale = f"task has no {VARIANT}; emitting stub"
        else:
            confidence = 1.0
            rationale = f"reference {VARIANT} for {task_id}"

    return emit({
        "task_id": task_id,
        "code": code,
        "loc": _sloc(code),
        "self_test_results": {"passed": 0, "failed": 0, "_note": "reference skill — no self-test run"},
        "rationale": rationale,
        "confidence": confidence,
    })


if __name__ == "__main__":
    sys.exit(main(sys.argv))
