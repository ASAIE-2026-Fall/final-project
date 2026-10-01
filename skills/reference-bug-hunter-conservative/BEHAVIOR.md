# BEHAVIOR — reference-bug-hunter-conservative

## Role in grading

A **low-FP-rate** opponent used to measure how often a Code Author's output is "obviously broken enough" to be detected by a strict, evidence-only inspector. Student Code Authors whose code passes the reference test cases will never be flagged by this skill.

## What it tests on the receiving side

When student is **Code Author**:
- A bug report from this skill is strong evidence the student's code is wrong.
- A `verdict=clean` from this skill is weak evidence — only tells us the code didn't crash on the reference probes.

## Why deterministic

Strategy is rule-based:
1. Run all reference `test_cases` against the input code.
2. For any crash with a traceback inside `<candidate>`, record the offending line.
3. If at least one crash line found, report **exactly one** bug at the first such line; classify as `edge_case` with `medium` severity. Otherwise `verdict=clean`.

No LLM involved — output is byte-identical for byte-identical input code.
