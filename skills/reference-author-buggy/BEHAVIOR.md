# BEHAVIOR — reference-author-buggy

## Role in grading

Pairwise opponent that emits code with **deliberately injected, well-known bug patterns**:
- empty-input crashes (e.g., `arr[0]` without an `if not arr:` guard)
- 0-vs-1 indexed parameter confusion
- missing quote-handling in parsers
- "obvious" recurrence typos

These are the kinds of bugs a competent Bug Hunter should catch with high recall. Used as 50% of the Bug Hunter's grade (the buggy-code F1 portion).

## Why deterministic

For recall to be a stable metric across runs, the buggy code must be byte-identical each time. The script reads `clean_code` / `buggy_code` from the task ground truth, so the *exact lines* expected to be flagged stay fixed.

## Ground truth

For each `task_id`, the expected `bug.line_start` / `bug.type` / `bug.severity` is in `bugs_in_buggy` of the task ground truth JSON. Tester / grader programs compare a Bug Hunter's report against this ground truth using line-overlap + type match.
