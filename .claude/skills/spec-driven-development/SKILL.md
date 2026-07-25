---
name: spec-driven-development
description: Spec-first workflow that prevents AI-coding drift on complex or ambiguous work. Use before/around implementation to turn a goal into an executable specification — EARS-style requirements, binary acceptance criteria, explicit scope/invariants, and a traceability matrix — that is the single source of truth code and tests are derived from. Sits between `strategic-engineering-planner` and `implementation-plan`. Covers writing the spec, deriving code + tests with traceability, and keeping the spec authoritative as requirements change. Routed to from `principal-production-engineer`.
---

# Spec-Driven Development

Make the specification — not the code — the source of truth. On complex or ambiguous work, an AI agent's failure mode is not slow generation; it is **drift**: confident, plausible code that quietly solves the wrong problem. A spec the agent must conform to, and tests derived from it, are what keep speed from turning into rework.

> Spec first. Tests from the spec. Code to pass the tests. Every change traces to a requirement.

## When to use — and when to skip

**Use** when the work is multi-file, ambiguous, externally-facing, safety/security-relevant, touches a contract (API, schema, protocol), or will be handed to an autonomous loop (`elves`, agents). The harder the problem and the longer the unattended run, the more a spec pays off.

**Skip** for trivial, obvious, single-file changes where a spec costs more than it saves. Use judgment — but bias toward a *short* spec for anything you'd be embarrassed to get subtly wrong.

## Where it sits in the flow

`strategic-engineering-planner` (is this worth doing? what's the architecture?) → **`spec-driven-development`** (what exactly must be true when it's done?) → `implementation-plan` (what are the ordered steps + gates?) → `principal-production-engineer` (build), with `test-driven-verification` deriving the tests from this spec and `karpathy-guidelines` governing throughout.

The planner answers *whether* and *how broadly*; this skill answers *exactly what*; the implementation plan answers *in what order*. Don't collapse them — the spec is the contract the checklist and tests are accountable to.

To put a finished spec in front of humans for review, load the `system-design-visualizer` skill — it renders the spec Markdown into a source-grounded HTML + SVG review artifact and refuses to invent anything the spec does not state.

## Reference index — progressive disclosure

Load only the file relevant to the current step.

- **[reference/writing_the_spec.md](reference/writing_the_spec.md)** — anatomy of a usable spec: EARS requirement syntax, binary acceptance criteria, explicit in-scope/out-of-scope, invariants and failure semantics, open-questions block. Templates and a quality bar for "is this spec executable yet."
- **[reference/deriving_code_and_tests.md](reference/deriving_code_and_tests.md)** — turning the spec into work: the requirement→test→code traceability matrix, deriving test cases from each acceptance criterion, slicing the spec into vertical increments, and handing the spec to coding agents.
- **[reference/keeping_specs_authoritative.md](reference/keeping_specs_authoritative.md)** — governance: detecting drift, the rule that code never silently diverges from spec (change the spec first, then the code), where the spec lives, review/change-control, and what to do when implementation reveals the spec was wrong.

## How to apply this material

1. Write the smallest spec that makes success **binary** — every acceptance criterion is something a test can pass or fail. Vague criteria ("works well", "is fast") are bugs in the spec.
2. Surface ambiguity as explicit **open questions** and resolve them *before* coding, not by silently picking an interpretation.
3. Derive tests from the spec (hand off to `test-driven-verification`), then code to the tests.
4. If implementation proves the spec wrong, **stop and update the spec**, then continue. The spec staying true is the whole point.
5. Keep it proportional — a one-paragraph spec for a small feature, a structured doc for a subsystem. The spec is a tool, not a deliverable for its own sake.
