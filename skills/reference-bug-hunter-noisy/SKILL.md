---
name: reference-bug-hunter-noisy
description: AIASE 2026 reference Bug Hunter (noisy). Probe-based, but with a deterministic seeded perturbation that drops ~30% of real bugs and injects ~30% fake bugs. Models an unreliable opponent.
version: 1.0.0
metadata:
  hermes:
    tags: [reference, bug-hunter, aiase-2026]
    category: code
---

# Reference Bug Hunter — Noisy

Deterministic Pairwise opponent that **simulates an unreliable inspector**. Built on the conservative probe analyzer, then perturbed with a seeded RNG: with probability ≈ 0.3 drop a real finding, and with probability ≈ 0.3 inject a fake finding at a randomly chosen non-empty line.

## When to Use

`/reference-bug-hunter-noisy {"task_id":"task_pair_001", "code":"...", "task_description":"..."}`.

## Procedure

1. Take the input JSON payload verbatim.
2. Invoke `python scripts/run.py '<payload>'`.
3. Emit the resulting fenced JSON block unchanged.

## Pitfalls

- This is not a useful Bug Hunter. It exists to model what happens when you pair with an unreliable opponent — useful for testing how robust your Code Author's `rationale` and `self_test_results` are when challenged with noise.

## Verification

Output is a Pairwise Bug Hunter contract JSON. Bugs are produced by the (seed, code-hash, task_id) triple, so output is byte-identical for byte-identical input.
