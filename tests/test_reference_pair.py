"""
Integration test for reference Pairwise opponents.

The reference Code Authors and Bug Hunters must agree on a deterministic
correspondence: when reference-author-buggy emits its canonical buggy code
for a task, reference-bug-hunter-aggressive should detect at least one bug
that overlaps the ground-truth `bugs_in_buggy` annotation.

We invoke each reference skill's scripts/run.py directly via subprocess so
no Hermes installation is required.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TASK_DIR = REPO_ROOT / "dev_set" / "pairwise" / "reference_tasks"

AUTHOR_BUGGY = REPO_ROOT / "skills" / "reference-author-buggy" / "scripts" / "run.py"
AUTHOR_CLEAN = REPO_ROOT / "skills" / "reference-author-clean" / "scripts" / "run.py"
AUTHOR_TRICKY = REPO_ROOT / "skills" / "reference-author-tricky" / "scripts" / "run.py"
HUNTER_AGGR = REPO_ROOT / "skills" / "reference-bug-hunter-aggressive" / "scripts" / "run.py"
HUNTER_CONS = REPO_ROOT / "skills" / "reference-bug-hunter-conservative" / "scripts" / "run.py"
HUNTER_NOISY = REPO_ROOT / "skills" / "reference-bug-hunter-noisy" / "scripts" / "run.py"

ALL_TASKS = sorted(p.stem for p in TASK_DIR.glob("task_pair_*.json")
                   if not p.stem.endswith("_GROUND_TRUTH"))


def _invoke(script: Path, payload: dict) -> dict:
    proc = subprocess.run(
        [sys.executable, str(script), json.dumps(payload, ensure_ascii=False)],
        capture_output=True, text=True, timeout=30, check=False,
    )
    out = proc.stdout
    # extract last fenced JSON
    import re
    m = re.findall(r"```json\s*\n(.*?)\n```", out, re.DOTALL | re.IGNORECASE)
    assert m, f"no fenced JSON in stdout:\n{out}\nstderr:\n{proc.stderr}"
    return json.loads(m[-1])


def _load_task(task_id: str) -> dict:
    return json.loads((TASK_DIR / f"{task_id}.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1. Reference authors emit the canonical code for known task_ids
# ---------------------------------------------------------------------------

def test_author_clean_emits_clean_code():
    for tid in ALL_TASKS:
        task = _load_task(tid)
        out = _invoke(AUTHOR_CLEAN, {
            "task_id": tid, "task_description": task["task_description"],
            "constraints": task["constraints"],
        })
        assert out["task_id"] == tid
        assert out["code"].strip() == task["clean_code"].strip(), f"clean code mismatch for {tid}"


def test_author_buggy_emits_buggy_code():
    for tid in ALL_TASKS:
        task = _load_task(tid)
        out = _invoke(AUTHOR_BUGGY, {
            "task_id": tid, "constraints": task["constraints"],
        })
        assert out["code"].strip() == task["buggy_code"].strip(), f"buggy code mismatch for {tid}"


def test_author_tricky_emits_tricky_code():
    for tid in ALL_TASKS:
        task = _load_task(tid)
        out = _invoke(AUTHOR_TRICKY, {
            "task_id": tid, "constraints": task["constraints"],
        })
        assert out["code"].strip() == task["tricky_code"].strip(), f"tricky code mismatch for {tid}"


def test_author_unknown_task_emits_stub():
    out = _invoke(AUTHOR_BUGGY, {
        "task_id": "definitely_not_a_real_task",
        "constraints": {"entry_function": "f"},
    })
    assert out["confidence"] == 0.0
    assert "def f" in out["code"]


# ---------------------------------------------------------------------------
# 2. Hunters' behavior matches their design
# ---------------------------------------------------------------------------

def test_aggressive_flags_buggy_code():
    """Aggressive hunter should report ≥1 bug on every buggy reference."""
    for tid in ALL_TASKS:
        task = _load_task(tid)
        out = _invoke(HUNTER_AGGR, {
            "task_id": tid, "task_description": task["task_description"],
            "code": task["buggy_code"],
        })
        assert out["verdict"] == "buggy", f"aggressive failed to flag {tid}"
        assert len(out["bugs"]) >= 1


def test_conservative_clean_on_clean_code():
    """Conservative hunter MUST NOT report bugs on the canonical clean code (FP=0)."""
    for tid in ALL_TASKS:
        task = _load_task(tid)
        out = _invoke(HUNTER_CONS, {
            "task_id": tid, "task_description": task["task_description"],
            "code": task["clean_code"],
        })
        assert out["verdict"] == "clean", \
            f"conservative false-positive on clean code for {tid}: {out}"


def test_conservative_catches_obvious_buggy_crashes():
    """Conservative must catch the bugs where a probe crashes (e.g., merge_intervals on [])."""
    # task_pair_001 buggy_code crashes on empty input. Conservative should flag it.
    task = _load_task("task_pair_001")
    out = _invoke(HUNTER_CONS, {
        "task_id": "task_pair_001", "task_description": task["task_description"],
        "code": task["buggy_code"],
    })
    assert out["verdict"] == "buggy"
    # GT bug is at line 3 (intervals[0] access without empty guard)
    assert any(b["line_start"] in (2, 3) for b in out["bugs"]), out


def test_noisy_is_seeded_deterministic():
    """Same input → same output (seeded RNG)."""
    task = _load_task("task_pair_001")
    payload = {"task_id": "task_pair_001",
               "task_description": task["task_description"],
               "code": task["buggy_code"]}
    a = _invoke(HUNTER_NOISY, payload)
    b = _invoke(HUNTER_NOISY, payload)
    assert a == b
