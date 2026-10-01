#!/usr/bin/env python3
"""code-author skill final output writer.

Reads JSON from argv[1] with the fields needed by the contract, validates shape,
and writes the Pairwise Code Author result object to AIASE_RESULT_PATH.
"""

from __future__ import annotations

import json
import os
import sys


def resolve_result_path() -> str:
    return os.environ.get("AIASE_RESULT_PATH") or os.path.join(os.getcwd(), "aiase_result.json")


def write_result(out: dict) -> None:
    path = resolve_result_path()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    try:
        os.replace(tmp, path)
    except PermissionError:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False)
        try:
            os.remove(tmp)
        except OSError:
            pass
    print(f"written ok -> {path}")


def _clamp_confidence(v) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, f))


def emit_contract(obj: dict) -> int:
    self_test = obj.get("self_test_results") or {}
    if not isinstance(self_test, dict):
        self_test = {"passed": 0, "failed": 0, "_warning": "non-object coerced"}
    self_test.setdefault("passed", 0)
    self_test.setdefault("failed", 0)

    out = {
        "task_id": str(obj.get("task_id", "")),
        "code": str(obj.get("code", "")),
        "loc": int(obj.get("loc", 0)) if str(obj.get("loc", "0")).lstrip("-").isdigit() else 0,
        "self_test_results": self_test,
        "rationale": str(obj.get("rationale", "")),
        "confidence": _clamp_confidence(obj.get("confidence", 0.5)),
    }
    write_result(out)
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        return emit_contract({
            "task_id": "", "code": "", "loc": 0,
            "self_test_results": {"passed": 0, "failed": 0},
            "rationale": "run.py invoked without argv payload",
            "confidence": 0.0,
        })
    try:
        payload = json.loads(argv[1])
        if not isinstance(payload, dict):
            raise ValueError("payload not an object")
    except (json.JSONDecodeError, ValueError) as e:
        return emit_contract({
            "task_id": "", "code": "", "loc": 0,
            "self_test_results": {"passed": 0, "failed": 0},
            "rationale": f"invalid argv JSON: {e}",
            "confidence": 0.0,
        })
    return emit_contract(payload)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
