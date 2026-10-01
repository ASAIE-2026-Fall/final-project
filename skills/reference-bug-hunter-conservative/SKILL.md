---
name: reference-bug-hunter-conservative
description: AIASE 2026 reference Bug Hunter (conservative). Only flags bugs proven by a deterministic probe crash. Used as a low-FP Pairwise opponent for student Code Author self-testing.
version: 1.0.0
metadata:
  hermes:
    tags: [reference, bug-hunter, aiase-2026]
    category: code
---

# Reference Bug Hunter — Conservative

Deterministic Pairwise opponent. Runs the task's reference test cases as probes against the input code, and only flags a bug when a probe **definitively crashed** with a traceback line we can pin. Otherwise reports `verdict=clean`. Low recall by design, near-zero false positives — the "high-precision baseline" against which student Code Authors are tested.

## When to Use

`/reference-bug-hunter-conservative {"task_id":"task_pair_001", "code":"...", "task_description":"..."}`.

## Procedure

1. Take the input JSON payload verbatim.
2. Invoke `python scripts/run.py '<payload>'`.
3. Emit the resulting fenced JSON block unchanged.

## Pitfalls

- This skill is intentionally low-recall — do not LLM-augment it. Adding speculative bugs would defeat the calibration purpose.

## Verification

Output is a Pairwise Bug Hunter contract JSON; at most one bug, only when a probe crash maps to a definite line.
