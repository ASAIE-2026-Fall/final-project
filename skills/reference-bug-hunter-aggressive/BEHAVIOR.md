# BEHAVIOR — reference-bug-hunter-aggressive

## Role in grading

A **high-recall, high-FP** opponent. Reports every probe failure and AST smell it can. Tests:
- whether a Code Author's code can survive a pessimistic auditor that flags everything.
- the resilience of a Code Author's `rationale` to deflect unfounded criticism (if measured).

## Strategy

1. Run all reference `test_cases` against the code.
2. For each crash → one `edge_case` bug at the crash line.
3. For each wrong-answer mismatch → one `logic_error` bug at the function definition line (we cannot localize the wrong-answer line, so we point at the function).
4. AST scan for smells:
   - mutable default arg (`def f(x=[]):` etc.) → `api_misuse`, `low`.
   - bare `except:` → `unhandled_input`, `low`.
   - `eval(` / `exec(` use on user input → `api_misuse`, `high`.
5. Cap at 5 bugs.

## Why deterministic

Same as the others — output is a deterministic function of the input code. No LLM, no randomness, reproducible across runs.
