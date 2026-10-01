# BEHAVIOR — reference-bug-hunter-noisy

## Role in grading

A **calibration / robustness** opponent. Lets us measure how the Code Author's grade changes when paired with an unreliable inspector: does the student's rationale + self_test_results stand up to noise, or do they collapse under pressure (e.g., a Bug Hunter that re-reports the same false claim repeatedly).

## Strategy

Built on the conservative probe path (real findings from crashes), then perturbed deterministically:

1. Compute `seed = (FIXED_SEED, task_id, sha256(code))`.
2. Run conservative probe → `real_lines`.
3. For each `real_line`: with `random.random() < DROP_P`, drop it.
4. Pick `inject_count = random.randint(0, 2)` random lines from `[1..N]` (where N is total code lines) that are **not** in `real_lines`; add them as fake bugs.
5. Return up to 3 bugs in total.

Constants (in script):
- `FIXED_SEED = 20260601` (audit-friendly: today's date in spec)
- `DROP_P = 0.30`
- `INJECT_P = 0.30`

## Why deterministic

`random.Random(seed)` with stable `seed` yields the same sequence each run. Across runs on identical input code, the perturbation is identical — auditable and reproducible.

## Audit notes

Each emitted bug includes `_synthetic: true` when fake-injected (consumed by graders, ignored by the standard contract enforcer). This lets the grading log distinguish "this skill said X" from "X actually exists".
