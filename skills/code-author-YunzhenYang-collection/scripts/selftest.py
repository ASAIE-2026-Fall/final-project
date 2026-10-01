#!/usr/bin/env python3
"""
code-author selftest harness.

Usage:
    python selftest.py '{
        "code": "def merge_intervals(intervals): ...",
        "constraints": {"entry_function": "merge_intervals", "max_loc": 500,
                        "imports_forbidden": ["os","sys"]},
        "sample_inputs": [
            {"input": [[[1,3],[2,4]]], "expected": [[1,4]]},
            {"input": [[]],            "expected": []}
        ]
    }'

Prints a single fenced JSON block:
    {"passed": int, "failed": int, "errors": [str],
     "sloc": int, "loc_violation": bool,
     "import_violations": [str]}

Deterministic. No LLM, no network. Uses `radon raw` for SLOC.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def _emit(obj: dict) -> int:
    sys.stdout.write("```json\n")
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, indent=2))
    sys.stdout.write("\n```\n")
    return 0


def compute_sloc(code: str) -> int:
    """以 `radon raw <file> --json` 計算 SLOC(規格書 §2.3)。Fallback: 簡單非空非註解行數。"""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(code)
        path = Path(f.name)
    try:
        try:
            proc = subprocess.run(
                ["radon", "raw", str(path), "--json"],
                capture_output=True, text=True, timeout=10, check=False,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                data = json.loads(proc.stdout)
                # radon returns {filepath: {sloc: int, ...}}
                if isinstance(data, dict):
                    for v in data.values():
                        if isinstance(v, dict) and "sloc" in v:
                            return int(v["sloc"])
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            pass
        # fallback
        count = 0
        for line in code.splitlines():
            s = line.strip()
            if s and not s.startswith("#"):
                count += 1
        return count
    finally:
        try:
            path.unlink()
        except OSError:
            pass


def find_import_violations(code: str, forbidden: list[str]) -> list[str]:
    """以 AST 找 import,比對禁用清單。"""
    if not forbidden:
        return []
    forbidden_set = {f.strip() for f in forbidden if f.strip()}
    found: list[str] = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return ["<syntax error — cannot static-check imports>"]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in forbidden_set:
                    found.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root = node.module.split(".")[0]
                if root in forbidden_set:
                    found.append(node.module)
    return sorted(set(found))


def run_sample(code: str, entry: str, sample: dict) -> tuple[bool, str]:
    ns: dict = {}
    try:
        exec(compile(code, "<candidate>", "exec"), ns)
    except Exception as e:
        return False, f"compile/exec error: {e!r}"
    fn = ns.get(entry)
    if not callable(fn):
        return False, f"entry function {entry!r} not defined"
    args = sample.get("input", [])
    expected = sample.get("expected")
    try:
        got = fn(*args) if isinstance(args, list) else fn(args)
    except Exception as e:
        return False, f"runtime error on input {args!r}: {e!r}"
    if got != expected:
        return False, f"mismatch on {args!r}: got {got!r}, expected {expected!r}"
    return True, ""


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        return _emit({"passed": 0, "failed": 0, "errors": ["usage: selftest.py '<json>'"],
                      "sloc": 0, "loc_violation": False, "import_violations": []})
    try:
        payload = json.loads(argv[1])
    except json.JSONDecodeError as e:
        return _emit({"passed": 0, "failed": 0, "errors": [f"argv JSON invalid: {e}"],
                      "sloc": 0, "loc_violation": False, "import_violations": []})

    code = str(payload.get("code", ""))
    constraints = payload.get("constraints", {}) or {}
    samples = payload.get("sample_inputs", []) or []

    sloc = compute_sloc(code)
    max_loc = int(constraints.get("max_loc", 500))
    loc_violation = sloc > max_loc
    import_violations = find_import_violations(code, constraints.get("imports_forbidden", []))

    entry = str(constraints.get("entry_function", ""))
    passed = 0
    failed = 0
    errors: list[str] = []
    if entry and samples:
        for s in samples:
            ok, err = run_sample(code, entry, s)
            if ok:
                passed += 1
            else:
                failed += 1
                errors.append(err)
    elif not entry:
        errors.append("constraints.entry_function not provided")

    return _emit({
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "sloc": sloc,
        "loc_violation": loc_violation,
        "import_violations": import_violations,
    })


if __name__ == "__main__":
    sys.exit(main(sys.argv))
