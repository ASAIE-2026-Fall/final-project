---
name: hello-aiase
description: Minimal smoke-test skill — echoes a greeting in the AIASE 2026 output contract. Use to verify the Hermes ↔ LiteLLM ↔ skill pipeline is wired up correctly.
version: 1.0.0
metadata:
  hermes:
    tags: [smoke-test, aiase-2026]
    category: utility
---

# Hello AIASE — Smoke Test

## When to Use

When the user invokes `/hello-aiase` with a JSON payload like `{"name":"world"}`. Use this skill to confirm Hermes can:

1. discover and load this skill,
2. invoke the script under `scripts/`,
3. relay the resulting fenced JSON block as the final output.

This skill performs **no LLM reasoning** — it just echoes structured input. If `/hello-aiase` works end-to-end, the rest of your AIASE 2026 setup is wired correctly.

## Procedure

1. Take the entire JSON payload from the user message verbatim (it should be an object; if missing, default to `{}`).
2. Invoke `scripts/run.py` with the JSON payload as a single argv string, e.g.:

   ```
   python scripts/run.py '{"name":"world"}'
   ```

3. The script will print a single fenced JSON block to stdout. **Emit that fenced JSON block as your final response, unchanged.** Do not add any reasoning text after it.

## Pitfalls

- Do not paraphrase the script output. The grader extracts the **last** fenced ```json``` block from stdout; anything after it that looks like JSON would be picked up instead.
- Do not call the LLM to "improve" the greeting — this skill is intentionally deterministic.

## Verification

- The final output must be a single fenced ```json``` block whose top-level is an object with fields `ok=true`, `skill="hello-aiase"`, and `echo=<the input>`.
- If input contains `task_id`, the output `task_id` must equal the input `task_id`.
