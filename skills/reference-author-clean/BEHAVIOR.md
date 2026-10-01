# BEHAVIOR — reference-author-clean

## Role in grading

Acts as a **Pairwise opponent** for `reference-bug-hunter-*` and student Bug Hunters. The output is a known-correct implementation of the task; a Bug Hunter that reports **any** bug here is producing a false positive (counts against its FP rate).

## What it tests on the receiving side

- **False-positive rate**: a good Bug Hunter must look at clean code and say `verdict=clean`, `bugs=[]`.
- **Robustness to "obvious" patterns**: clean code may still contain patterns that naive Bug Hunters mis-flag (e.g., `intervals.sort()` is in-place but not a bug per spec).

## Why it must be deterministic

Reference behavior must be reproducible across grading runs. Any LLM "noise" would make the FP rate measurement unstable and unfair. Therefore the script reads the canonical clean code from the task ground truth file and outputs it verbatim — no LLM in the loop on this skill's side.

## Inputs it accepts

Any payload conforming to the Code Author input contract. If `task_id` is unknown (not in `dev_set/pairwise/reference_tasks/`), the script returns a degenerate stub that compiles but does not implement the task — this is intentional, so unknown `task_id`s are detected as such by the grader.
