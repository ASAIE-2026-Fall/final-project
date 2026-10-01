#!/usr/bin/env python3
"""
bug-hunter analyzer — deterministic edge-input probing.

Usage:
    python analyze.py '{
        "code": "...",
        "entry_function": "<entry_name>",
        "edge_inputs": [          # optional; if omitted, a generic battery is used
            {"input": [[]],          "label": "empty container"},
            {"input": [0],           "label": "zero"}
        ]
    }'

Prints a single fenced JSON block:
    {"entry_found": bool,
     "ast_lines": {"entry_def": int, "return_lines": [int], "loop_lines": [int]},
     "probes": [{"label": str, "outcome": "ok"|"crash"|"timeout", "error": str}],
     "suspicious_lines": [int],
     "summary": str}

This is the deterministic side of the bug-hunter; the LLM uses it as evidence,
but still makes the final bug-vs-not-bug judgment.
"""

from __future__ import annotations

import ast
import json
import signal
import sys
import traceback
from contextlib import contextmanager


def _emit(obj: dict) -> int:
    sys.stdout.write("```json\n")
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, indent=2))
    sys.stdout.write("\n```\n")
    return 0


def _ast_features(code: str, entry: str) -> dict:
    out = {"entry_def": -1, "return_lines": [], "loop_lines": []}
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == entry:
            out["entry_def"] = node.lineno
        if isinstance(node, ast.Return) and node.lineno:
            out["return_lines"].append(node.lineno)
        if isinstance(node, (ast.For, ast.While)) and node.lineno:
            out["loop_lines"].append(node.lineno)
    out["return_lines"].sort()
    out["loop_lines"].sort()
    return out


class _Timeout(Exception):
    pass


@contextmanager
def _time_limit(seconds: float):
    """SIGALRM-based timeout. POSIX only; on Windows the context is a no-op and
    an infinite-loop probe will not be interrupted — the grading environment
    (Linux) provides the real timeout guarantee."""
    if not hasattr(signal, "SIGALRM"):
        yield
        return
    def _handler(signum, frame):
        raise _Timeout("probe timed out")
    old = signal.signal(signal.SIGALRM, _handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


def _default_battery() -> list[dict]:
    """
    Task-agnostic shape probes. Each item passes a single positional argument
    of a common "shape category" (empty container, singleton, two-element,
    extremes, None). The probe layer only judges "crash vs ok vs timeout" and
    pins a line if the traceback points inside <candidate>; whether a crash
    is a *real* bug is your skill's call.

    Probes that fail with TypeError because the entry function has a different
    arity will not contribute a `bad_line` (their traceback is outside
    <candidate>), so wrong-arity noise does not pollute suspicious_lines.

    For more targeted probing, callers should pass `edge_inputs` in the
    payload instead of relying on this generic battery.
    """
    return [
        {"input": [[]],                "label": "empty list"},
        {"input": [[0]],               "label": "singleton list"},
        {"input": [[0, 0]],            "label": "two-element list (repeats)"},
        {"input": [[0, 1]],            "label": "two-element list (distinct)"},
        {"input": [""],                "label": "empty string"},
        {"input": ["a"],               "label": "single-char string"},
        {"input": [0],                 "label": "zero"},
        {"input": [-1],                "label": "negative integer"},
        {"input": [10**6],             "label": "large integer"},
        {"input": [None],              "label": "None"},
    ]


def _task_aware_battery(entry: str) -> list[dict]:
    """Small public-reference probes keyed by entry function name."""
    cases: dict[str, list[dict]] = {
        "merge_intervals": [
            {"input": [[]], "expected": [], "label": "empty intervals"},
            {"input": [[[1, 2], [2, 3]]], "expected": [[1, 3]], "label": "touching intervals"},
            {"input": [[[5, 7], [1, 3], [2, 4]]], "expected": [[1, 4], [5, 7]], "label": "unsorted overlap"},
        ],
        "binary_search": [
            {"input": [[], 5], "expected": -1, "label": "empty array"},
            {"input": [[5], 5], "expected": 0, "label": "single present"},
            {"input": [[1, 2, 3, 4, 5], 5], "expected": 4, "label": "last element"},
            {"input": [[1, 2, 3, 4, 5], 0], "expected": -1, "label": "below range"},
        ],
        "parse_csv_line": [
            {"input": [""], "expected": [""], "label": "empty record"},
            {"input": ["a,\"b,c\",d"], "expected": ["a", "b,c", "d"], "label": "quoted comma"},
            {"input": ["\"hello \"\"world\"\"\""], "expected": ["hello \"world\""], "label": "escaped quote"},
        ],
        "unique_paths": [
            {"input": [1, 1], "expected": 1, "label": "one by one"},
            {"input": [3, 3], "expected": 6, "label": "square grid"},
            {"input": [3, 7], "expected": 28, "label": "rectangular grid"},
            {"input": [0, 5], "expected": 0, "label": "zero rows"},
        ],
        "kth_smallest": [
            {"input": [[3, 1, 2], 1], "expected": 1, "label": "first smallest"},
            {"input": [[3, 1, 2], 3], "expected": 3, "label": "last valid k"},
            {"input": [[5], 2], "expected": None, "label": "k too large"},
            {"input": [[1, 1, 1], 2], "expected": 1, "label": "duplicates count"},
        ],
    }
    return cases.get(entry, [])


def _jsonish(value):
    try:
        return json.loads(json.dumps(value, ensure_ascii=False))
    except (TypeError, ValueError):
        return repr(value)


def _probe(code: str, entry: str, sample: dict, timeout_sec: float) -> dict:
    ns: dict = {}
    try:
        exec(compile(code, "<candidate>", "exec"), ns)
    except Exception as e:
        return {"label": sample.get("label", "?"), "outcome": "crash",
                "error": f"compile/exec error: {e!r}"}
    fn = ns.get(entry)
    if not callable(fn):
        return {"label": sample.get("label", "?"), "outcome": "crash",
                "error": f"entry function {entry!r} not defined"}
    args = sample.get("input", [])
    try:
        with _time_limit(timeout_sec):
            actual = fn(*args) if isinstance(args, list) else fn(args)
        if "expected" in sample and actual != sample.get("expected"):
            return {
                "label": sample.get("label", "?"),
                "outcome": "mismatch",
                "error": "",
                "expected": _jsonish(sample.get("expected")),
                "actual": _jsonish(actual),
            }
        return {"label": sample.get("label", "?"), "outcome": "ok", "error": ""}
    except _Timeout as e:
        return {"label": sample.get("label", "?"), "outcome": "timeout", "error": str(e)}
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)
        # 找 traceback 中對應 <candidate> 的最後一行,推測 suspicious line
        bad_line = -1
        for f in tb:
            if f.filename == "<candidate>" and f.lineno:
                bad_line = f.lineno
        return {
            "label": sample.get("label", "?"),
            "outcome": "crash",
            "error": f"{type(e).__name__}: {e}",
            "bad_line": bad_line,
        }


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        return _emit({"entry_found": False, "ast_lines": {}, "probes": [],
                      "suspicious_lines": [], "summary": "usage: analyze.py '<json>'"})
    try:
        payload = json.loads(argv[1])
    except json.JSONDecodeError as e:
        return _emit({"entry_found": False, "ast_lines": {}, "probes": [],
                      "suspicious_lines": [], "summary": f"argv JSON invalid: {e}"})

    code = str(payload.get("code", ""))
    entry = str(payload.get("entry_function", ""))
    samples = payload.get("edge_inputs") or _task_aware_battery(entry) or _default_battery()
    timeout_sec = float(payload.get("timeout_sec", 1.0))

    ast_lines = _ast_features(code, entry)
    entry_found = ast_lines.get("entry_def", -1) > 0

    probes = []
    suspicious: set[int] = set()
    for s in samples:
        r = _probe(code, entry, s, timeout_sec)
        probes.append(r)
        if r["outcome"] != "ok" and r.get("bad_line", -1) > 0:
            suspicious.add(r["bad_line"])

    crashes = sum(1 for r in probes if r["outcome"] == "crash")
    timeouts = sum(1 for r in probes if r["outcome"] == "timeout")
    mismatches = sum(1 for r in probes if r["outcome"] == "mismatch")
    summary = (
        f"{len(probes)} probes; {crashes} crash, {timeouts} timeout, "
        f"{mismatches} mismatch, {len(probes)-crashes-timeouts-mismatches} ok; "
        f"suspicious_lines={sorted(suspicious)}"
    )

    return _emit({
        "entry_found": entry_found,
        "ast_lines": ast_lines,
        "probes": probes,
        "suspicious_lines": sorted(suspicious),
        "summary": summary,
    })


if __name__ == "__main__":
    sys.exit(main(sys.argv))
