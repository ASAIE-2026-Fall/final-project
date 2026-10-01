---
name: code-author-YunzhenYang-collection
description: Implement a Python function and emit the AIASE 2026 Code Author contract.
version: 0.3.0
metadata:
  hermes:
    tags: [code, python, aiase-2026]
    category: code
---

# Code Author Skill (Pairwise Track)

## When to Use

Triggered by `/code-author-YunzhenYang-collection` with JSON containing `task_id`,
`task_description`, and `constraints` (`entry_function`, `max_loc`, `imports_forbidden`).
The skill must write the AIASE 2026 Pairwise Code Author contract to the result
file.

Trigger example:

```text
/code-author-YunzhenYang-collection {"task_id":"task_042","task_description":"Implement merge_intervals(intervals): merge overlapping intervals, empty input returns [].","constraints":{"entry_function":"merge_intervals","max_loc":500,"imports_forbidden":["os","sys"]}}
```

## Procedure

Do not narrate. Do not plan aloud. Do not list files. Do not search the repo.
Use exactly one self-test command in step 3 and exactly one `run.py` command in
step 4.

Quality rules:
- Define exactly `constraints.entry_function`.
- Guard empty, `None`, or zero-like invalid input before indexing.
- Prefer simple built-ins and direct algorithms.
- Do not import modules unless the task requires them and they are not forbidden.
- Preserve ordering, sorting, duplicate, and boundary requirements from `task_description`.
- Keep the implementation total and deterministic for valid inputs: return a specified fallback such as `[]`, `-1`, `0`, or `None` when the task description defines one.
- Avoid mutating input arguments unless the task explicitly asks for in-place behavior.

Steps:

1. Draft one compact Python implementation immediately from `task_description`.

2. Build exactly 3 `sample_inputs`:
   - empty or minimal input
   - normal representative input
   - hidden-style boundary case, chosen from the task text: duplicates, touching ranges, unsorted input, invalid or edge `k`, negative/zero values, one-element inputs, repeated characters, quoted delimiters, or first/last element cases

   Wrapping rule: `input` is always the list of positional arguments.
   For one-argument `f(x)`, use `{"input": [<x>], "expected": <result>}`.
   Examples: `f([])` -> `{"input": [[]], "expected": []}`;
   `merge_intervals([[1,5]])` -> `{"input": [[[1,5]]], "expected": [[1,5]]}`;
   `add(1,2)` -> `{"input": [1,2], "expected": 3}`.

   Sample quality rule: the third sample must target a likely hidden-test failure mode, not merely another normal case. Do not add more than 3 samples.

3. Run selftest exactly once:

```bash
python skills/code-author-YunzhenYang-collection/scripts/selftest.py '{"code":"<candidate code>","constraints":<constraints>,"sample_inputs":[...]}'
```

4. Immediately call `scripts/run.py` to write the result file and stop. Use
`selftest.py`'s `sloc` as `loc` and copy the full selftest object into
`self_test_results`. Do not hand-write a JSON answer in the conversation.

```bash
python skills/code-author-YunzhenYang-collection/scripts/run.py '{"task_id":"<exact task_id from input>","code":"<complete Python implementation>","loc":<integer sloc from selftest>,"self_test_results":<selftest output object>,"rationale":"<one concise sentence>","confidence":<0.0-1.0>}'
```

## Pitfalls

- Missing empty-input handling: guard before indexing.
- Wrong `sample_inputs` wrapping: `input` is the positional argument list; for one list argument, use one extra wrapper.
- Off-by-one and boundary cases: include first/last/touching/duplicate cases when relevant.
- Sorting and duplicate semantics: preserve duplicate counts unless the task asks for unique values; do not sort output unless order is specified or irrelevant.
- Invalid bounds: when the task defines behavior for out-of-range `k`, empty input, zero dimensions, or missing values, implement that branch explicitly.
- Forbidden imports: do not import modules listed in `constraints.imports_forbidden`.
- Timeout risk: one draft, exactly one selftest command, one run.py command to
  write the result file, then stop.

## Verification

- `task_id` is identical to input.
- `code` defines exactly `constraints.entry_function`.
- `loc` is an integer and `self_test_results` contains `passed` and `failed`.
- `confidence` is a number in `[0.0, 1.0]`.
- `scripts/run.py` writes the JSON object to `AIASE_RESULT_PATH`, or
  `./aiase_result.json` if that environment variable is not set.
