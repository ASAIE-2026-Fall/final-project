---
name: reference-author-tricky
description: AIASE 2026 reference Code Author (tricky). Returns an implementation with SUBTLE bugs (off-by-one in rare boundaries, escape-handling corner cases, etc.). High bar for Bug Hunter discrimination.
version: 1.0.0
metadata:
  hermes:
    tags: [reference, code-author, aiase-2026]
    category: code
---

# Reference Author — Tricky

Deterministic Pairwise opponent. Emits an implementation with **subtle bugs** — defects that pass common tests but fail on rarer boundaries. Used to measure a Bug Hunter's ability to discriminate beyond surface-level issues.

## When to Use

`/reference-author-tricky {"task_id":"task_pair_001", ...}`. Standard Code Author input contract.

## Procedure

1. Take the input JSON payload verbatim.
2. Invoke `python scripts/run.py '<payload>'`.
3. Emit the resulting fenced JSON block unchanged.

## Pitfalls

- Do not "fix" the output. The subtle bugs are the point.

## Verification

Output is a single fenced ```json``` block in the Code Author contract. For known `task_id`, `code` is the canonical tricky implementation; expected bugs are listed in `dev_set/pairwise/reference_tasks/<task_id>.json` under `bugs_in_tricky`.
