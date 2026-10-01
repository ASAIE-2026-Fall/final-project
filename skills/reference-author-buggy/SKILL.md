---
name: reference-author-buggy
description: AIASE 2026 reference Code Author (buggy). Returns an implementation containing OBVIOUS bugs for the requested task. Used as a Pairwise opponent to test Bug Hunter recall on common bugs.
version: 1.0.0
metadata:
  hermes:
    tags: [reference, code-author, aiase-2026]
    category: code
---

# Reference Author — Buggy

Deterministic Pairwise opponent. Emits an implementation with **known, obvious bugs** for the requested task — used to measure a Bug Hunter's recall on common defect patterns (empty-input crashes, off-by-one in single-element cases, missing edge handling, etc.).

## When to Use

`/reference-author-buggy {"task_id":"task_pair_001", ...}`. Standard Code Author input contract.

## Procedure

1. Take the input JSON payload verbatim.
2. Invoke `python scripts/run.py '<payload>'`.
3. Emit the resulting fenced JSON block unchanged.

## Pitfalls

- Do not "fix" the output. The whole point of this skill is to produce known buggy code so the Bug Hunter has something to catch.

## Verification

Output is a single fenced ```json``` block in the Code Author contract. For known `task_id`, `code` is the canonical buggy implementation; expected bugs are listed in `dev_set/pairwise/reference_tasks/<task_id>.json` under `bugs_in_buggy`.
