---
name: test-driven-verification
description: Verification-first workflow — prove code actually does what the spec requires, at speed. Use when implementing or hardening any nontrivial change: derive tests from acceptance criteria before coding, loop red → green → refactor, and capture hard evidence behavior works (unit/property tests for logic, integration tests for boundaries, Playwright/tmux artifacts for UI and flows), gated by binary merge criteria. Covers test design, the red-green loop, and evidence capture. Pairs with `spec-driven-development` and `implementation-plan`; routed to from `principal-production-engineer`.
---

# Test-Driven Verification

Speed without verification is just faster breakage. The way to ship complex software fast is to make "does it work?" a question with a **mechanical, repeatable answer** — a test that passes, an artifact that shows the behavior — not a vibe check. Write the check first, then make it pass.

> A claim of "done" without a green check the user can re-run is an opinion, not a result.

## When to use

- Implementing a feature, bugfix, or refactor of any real size.
- Hardening existing code for production.
- Closing the loop for an autonomous run (`elves`, agents) — the gate is what lets the loop self-correct without you.

Compress for trivial edits, but never skip the "prove it" step for anything externally-visible or invariant-bearing.

## The loop

1. **Derive** the checks from acceptance criteria (from `spec-driven-development`, if present) — before writing implementation.
2. **Red** — write the test; watch it fail for the right reason. A test that passes before you've written the code tests nothing.
3. **Green** — minimal code to pass.
4. **Refactor** — clean up with the test as a safety net.
5. **Capture evidence** — for anything you can't fully assert in a unit test (UI, flows, integrations), record an artifact that shows it working.
6. **Gate** — the merge criterion is binary and stated up front: which checks must be green, what coverage of the spec, what evidence attached.

## Reference index — progressive disclosure

Load only the file relevant to the current step.

- **[reference/test_design.md](reference/test_design.md)** — what to test and how: turning each acceptance criterion into cases, the test pyramid (unit/integration/E2E proportions), property-based tests for invariants, table-driven cases, fuzzing parsers/protocols, fixtures vs mocks, and what *not* to test.
- **[reference/red_green_loop.md](reference/red_green_loop.md)** — running the loop in practice: writing a failing test first, the smallest-green discipline, regression test from every bug, binary merge gates, CI wiring, and handling/quarantining flaky tests honestly.
- **[reference/evidence_capture.md](reference/evidence_capture.md)** — proving behavior that a unit test can't: Playwright for browser flows (screenshots/video/traces), `tmux`-driven CLI/TUI capture, integration/E2E harnesses, minimal repro scripts, and attaching artifacts to the PR so the reviewer re-runs nothing on faith.

## How to apply this material

1. State the **merge gate** before coding: the exact commands and evidence required to call it done.
2. Derive checks from the spec/criteria; if a criterion can't be turned into a check, the criterion is too vague — push it back to `spec-driven-development`.
3. Prefer the **strongest local signal**: type checker → unit/property tests → integration → E2E → captured artifact. Use the cheapest one that actually proves the claim.
4. Never report verification you didn't run. If a check can't run locally, say so and give the exact command.
5. Every fixed bug leaves behind a regression test that fails on the old code and passes on the new.

This is the Python/JS/any-language operationalization of `principal-production-engineer`'s verification discipline — and the gate that makes `spec-driven-development` enforceable rather than aspirational.
