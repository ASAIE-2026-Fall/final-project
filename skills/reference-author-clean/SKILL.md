---
name: reference-author-clean
description: AIASE 2026 reference Code Author (clean). Returns a correct, bug-free implementation for the requested pairwise task. Used as a Pairwise opponent for local self-testing of student Bug Hunter skills.
version: 1.0.0
metadata:
  hermes:
    tags: [reference, code-author, aiase-2026]
    category: code
---

# Reference Author — Clean

This is a **deterministic reference skill** used as a Pairwise opponent. It does not call the LLM for code generation — it looks up the requested task in `dev_set/pairwise/reference_tasks/` and returns the canonical clean implementation. Pairs with `reference-bug-hunter-*` for student self-testing.

## When to Use

When the user invokes `/reference-author-clean {"task_id":"task_pair_001", ...}`. Honors the standard Code Author input contract.

## Procedure

1. Take the input JSON payload verbatim.
2. Invoke `python scripts/run.py '<payload>'`. The script reads the task ground truth and emits a fenced JSON block in the Pairwise Code Author contract.
3. Emit that fenced JSON block as your final response, unchanged.

## Pitfalls

- This skill is deterministic by design — do not "improve" the output with LLM reasoning. The reference value is exactly the clean implementation in the ground truth.

## Verification

Output is a single fenced ```json``` block: `{task_id, code, loc, self_test_results, rationale, confidence}`. For known `task_id`, `confidence=1.0` and `code` is the canonical clean implementation.
