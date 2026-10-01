# BEHAVIOR — reference-author-tricky

## Role in grading

Pairwise opponent emitting code with **subtle, single-line defects** — typically:
- strict-vs-loose comparison (`<` vs `<=`) on a boundary case the simple tests miss
- inconsistent bound conventions (mixing exclusive upper bound with inclusive shrinkage)
- silent dedup (e.g., `set(nums)` when duplicates should count)
- padded DP table with inconsistent indexing

These are bugs that:
- pass naive self-tests written by the buggy author (common inputs OK)
- only manifest on specific edge inputs the Bug Hunter must construct or reason about
- distinguish a high-quality Bug Hunter from a lucky pattern-matcher

## Why deterministic

Same reason as `reference-author-buggy`: stable byte-identical output so grading is reproducible. Subtle bugs must land on the same line each time for ground-truth comparison to work.

## Ground truth

`bugs_in_tricky` field of each task ground truth JSON. A Bug Hunter is expected to:
1. flag at least the listed line range,
2. classify with the listed `type`,
3. assign a `severity` consistent with the spec's calibration rule (rare-trigger → typically `medium`).
