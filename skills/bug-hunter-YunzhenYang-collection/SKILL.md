---
name: bug-hunter-YunzhenYang-collection
description: Audit a Python function for bugs against its task description, emit a structured bug report per the AIASE 2026 Pairwise Bug Hunter contract.
version: 0.1.0
metadata:
  hermes:
    tags: [code, audit, aiase-2026]
    category: code
---

# Bug Hunter Skill (Pairwise Track)

## When to Use

When the user sends a JSON payload with `code` (Python source), `task_description`, and `task_id`. The skill must produce a structured bug report whose `bugs[]` matches actual bugs (Jaccard-ish line+type overlap), with low false-positive rate on clean code.

Trigger example:

```
/bug-hunter-YunzhenYang-collection {"task_id":"task_042",
  "code":"def merge_intervals(intervals): ...",
  "task_description":"Merge overlapping intervals, empty input returns []."}
```

## Procedure

1. **Parse** the payload. Read `code` line-by-line (1-indexed); read the task description for the spec.
2. **Probe** the code by running `python skills/bug-hunter-YunzhenYang-collection/scripts/analyze.py` with the code + task description + entry function name. The script:
   - parses the AST to extract function name + parameters,
   - runs the function on a battery of deterministic edge inputs (empty, single-element, extremes),
   - returns per-input crash / mismatch / OK plus suspicious line ranges.
3. **Review** the analyzer signals. If all probes are `ok` and `suspicious_lines` is empty, prefer `verdict=clean` with `bugs=[]`. If `suspicious_lines` is empty but any probe has `outcome=mismatch`, read the code line-by-line anyway; focus on loop conditions, return expressions, boundary checks, index math, and missing branches for required input cases. For each suspicious line range or mismatch-backed defect, decide:
   - **bug or not** (don't over-report — false positives are penalized).
   - **type**: one of `off_by_one` / `null_deref` / `type_error` / `logic_error` / `edge_case` / `api_misuse` / `inefficient` / `unhandled_input` (see spec §2.3).
     If a probe crashes on an empty/null/boundary input that the task description says must be handled, classify it as `edge_case` rather than `type_error` or `null_deref`.
     If a mismatch is caused by a one-step index/loop-bound error (for example `k` vs `k-1`, `<` vs `<=`, or skipping the final candidate), classify it as `off_by_one`.
     If a mismatch shows a required class of inputs is not implemented at all (for example quoted CSV fields, escaped quotes, duplicates that must count, or invalid `k` bounds), classify it as `unhandled_input`.
     If a mismatch comes from an incorrect recurrence, formula, comparison, or state update where the input class is otherwise handled, classify it as `logic_error`.
     If the code mutates inputs when the task implies a pure return value, report only if that mutation changes the required observable behavior.
     If the analyzer probe is generic and the task description does not require that input shape, treat it as evidence to inspect manually, not as an automatic bug.
   - **severity**: `critical` / `high` / `medium` / `low` — calibrated to "how easily triggered + how severe".
   - **suggested_fix**: actionable, specific.
4. **Verdict**: `clean` if no bugs found, `buggy` otherwise. If unsure whether a finding is a real spec violation, do not report it; false positives on clean code are penalized. If `verdict=clean`, `bugs[]` must be `[]`.
5. **Write** the contract by running the command below. Do not hand-write a JSON answer in the conversation; the grader reads the result file.

```bash
python skills/bug-hunter-YunzhenYang-collection/scripts/run.py '{"task_id":"<task_id>","verdict":"<buggy|clean>","bugs":<bugs array>,"confidence":<0.0-1.0>}'
```

## Pitfalls

- **Over-reporting** (always reporting many bugs) destroys score — clean code FP rate is 25% of your grade.
- **Under-reporting** (always `verdict=clean`) also destroys score — F1 on buggy code is 50%.
- **Wrong severity calibration**: empty-input crash = `medium` (edge), wrong-answer-on-common-input = `high`/`critical`. See spec §2.3.
- **Wrong line numbers**: 1-indexed, point at the smallest line range that contains the bug. Don't point at the function signature line for an off-by-one in the loop.
- **Mismatch without traceback**: inspect the return expression, loop bounds, final-element handling, duplicate handling, and invalid-bound branches; report the smallest responsible line range.
- **Spec ambiguity**: if the task does not specify behavior for an input, do not report that input as a bug unless the code also fails a clearly required case.

## Verification

The result file written by `scripts/run.py` is a JSON object with:

- `task_id` (must equal input)
- `verdict` (`"buggy"` or `"clean"`)
- `bugs` (array of bug objects with `line_start`, `line_end`, `severity`, `type`, `description`, `suggested_fix`; **must be `[]` when verdict=clean**)
- `confidence` (number in `[0.0, 1.0]`)

The script writes to `AIASE_RESULT_PATH`, or `./aiase_result.json` if that
environment variable is not set.
