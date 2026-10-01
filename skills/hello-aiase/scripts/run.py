#!/usr/bin/env python3
"""hello-aiase smoke-test entry point — deterministic, no LLM, no network."""

from __future__ import annotations

import json
import sys


def main(argv: list[str]) -> int:
    raw = argv[1] if len(argv) > 1 else "{}"
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            payload = {"_warning": "input was not a JSON object", "_raw": raw}
    except json.JSONDecodeError as e:
        payload = {"_warning": f"invalid JSON: {e}", "_raw": raw}

    out: dict = {
        "ok": True,
        "skill": "hello-aiase",
        "echo": payload,
        "greeting": f"hello, {payload.get('name', 'AIASE 2026')}!",
    }
    if "task_id" in payload:
        out["task_id"] = payload["task_id"]

    # 輸出契約:單一 fenced JSON 區塊。
    sys.stdout.write("```json\n")
    sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=2))
    sys.stdout.write("\n```\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
