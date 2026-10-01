#!/usr/bin/env python3
"""text2sql skill final output writer.

Reads a JSON payload from argv[1], validates the minimal output shape, and writes
the Basic Track result object to AIASE_RESULT_PATH.
"""

from __future__ import annotations

import json
import os
import sys


CONTRACT_FIELDS = ("task_id", "sql", "rationale", "confidence")


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


def emit_contract(obj: dict) -> int:
    out = {
        "task_id": str(obj.get("task_id", "")),
        "sql": str(obj.get("sql", "")).strip(),
        "rationale": str(obj.get("rationale", "")),
        "confidence": _clamp_confidence(obj.get("confidence", 0.5)),
    }
    # 任何 extra fields 一律忽略(規格書 §1.4 #3)。
    write_result(out)
    return 0


def _clamp_confidence(v) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.0
    if f < 0.0:
        return 0.0
    if f > 1.0:
        return 1.0
    return f


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        # 失敗也要產出契約 JSON,不可只噴錯(規格書 §1.4 #7)。
        return emit_contract({
            "task_id": "",
            "sql": "",
            "rationale": "run.py invoked without argv payload",
            "confidence": 0.0,
        })

    try:
        payload = json.loads(argv[1])
        if not isinstance(payload, dict):
            raise ValueError("payload not an object")
    except (json.JSONDecodeError, ValueError) as e:
        return emit_contract({
            "task_id": "",
            "sql": "",
            "rationale": f"invalid argv JSON: {e}",
            "confidence": 0.0,
        })

    return emit_contract(payload)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
