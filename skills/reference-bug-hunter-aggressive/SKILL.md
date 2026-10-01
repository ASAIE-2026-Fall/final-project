---
name: reference-bug-hunter-aggressive
description: AIASE 2026 reference Bug Hunter (aggressive). Reports any probe failure as a bug AND flags AST smells. High recall, high FP. Used as a maximalist Pairwise opponent.
version: 1.0.0
metadata:
  hermes:
    tags: [reference, bug-hunter, aiase-2026]
    category: code
---

# Reference Bug Hunter — Aggressive

Deterministic Pairwise opponent. Reports a bug for **every** probe failure (crash or wrong answer), plus a handful of AST-level smells (mutable default args, bare `except`, etc.). High recall, high false-positive rate.

## When to Use

`/reference-bug-hunter-aggressive {"task_id":"task_pair_001", "code":"...", "task_description":"..."}`.

## Procedure

1. Take the input JSON payload verbatim.
2. Invoke `python scripts/run.py '<payload>'`.
3. Emit the resulting fenced JSON block unchanged.

## Pitfalls

- Not "the right opponent" — its high FP rate is intentional. Use it to see how your code performs under a pessimistic auditor.

## Verification

Output is a Pairwise Bug Hunter contract JSON. May report multiple bugs (cap 5). `verdict=clean` only when no probes fail AND no AST smells found.
