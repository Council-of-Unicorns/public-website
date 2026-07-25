---
name: implementation-plan
description: Turn a locked system design doc into a step-by-step IMPLEMENTATION_PLAN.md that coding agents can execute autonomously. Use after the design is settled and before any implementation code is written. Produces a checklist-first document with vertical-slice steps, binary acceptance gates, property tests tied to invariants, a golden-path integration test, an explicit iteration loop (including rewrite-from-scratch as a stuck-protocol option), and design tensions surfaced for human review. Companion to `strategic-engineering-planner` (which produces the architectural roadmap) and `principal-production-engineer` (which executes against the plan).
---

# Implementation Plan

Turn a locked system design into a step-by-step IMPLEMENTATION_PLAN.md
that coding agents can execute autonomously. Produces a checklist-first
document with binary acceptance gates, property tests, an iteration
loop, and explicit design tensions for human review.

## When to use

After a system design document is locked (the "what") and before any
implementation code is written. Companion to:

- **`strategic-engineering-planner`** — that skill produces the
  architectural roadmap. This skill turns it into a per-step execution
  checklist.
- **`principal-production-engineer`** — that skill enforces
  doctrine during implementation. This skill bakes the doctrine *into
  the plan* as property gates and CI guards before any code is
  written.

Use this skill when the user asks for:

- "an implementation plan / execution plan / rollout plan"
- "break this design into steps / a checklist / shippable PRs"
- "guide coding agents to implement this"
- "stage the migration / sequence the rewrite"

Skip when the work is trivial (<1 hour, single file, no test surface).

## What this skill produces

A single `IMPLEMENTATION_PLAN.md` at the repo root with this exact
shape:

1. **The steps at a glance** — top-level checklist of every step
   title, plus a dependency graph. Readers see the spine in 30 seconds.
2. **Properties to preserve (P1, P2, …)** — the system's invariants,
   each tied to a measurable test in a specific step. Properties are
   *gates*, not aspirations.
3. **How to execute** — vertical-slicing, tests-first, binary
   acceptance, rewrite-from-scratch-when-easier.
4. **Step 0 … Step N** — each with the same shape (Goal, Why now,
   Tests first, Implementation, Integration check, Acceptance,
   Depends on).
5. **Definition of done (whole plan).**
6. **Appendices** — golden-path integration test (§A), iteration loop
   (§B), out of scope (§C), design tensions surfaced for review (§D).

The full template lives at
[reference/IMPLEMENTATION_PLAN_TEMPLATE.md](reference/IMPLEMENTATION_PLAN_TEMPLATE.md).

## North star

> **Steps are vertical slices that ship one capability end-to-end and
> leave the system working. Properties are invariants gated by tests.
> The integration test is the spine. Doctrine is mechanically enforced,
> not aspirational. When stuck, rewrite the file from scratch.**

---

## The methodology (seven phases)

### Phase 1: Pre-flight evaluation

Read the design doc. Read the current codebase. Answer three questions
before writing any plan content:

1. **Migrate or rewrite from scratch?**
   - Migrate when the codebase has *substantial* aligned work — the
     renderer is in good shape, the deployment works, only the
     analysis half violates doctrine.
   - Rewrite when starting from a near-empty repo, when the existing
     code is fundamentally misaligned, or when migration cost exceeds
     rewrite cost.
   - **State the recommendation explicitly** at the top of the plan
     with reasoning. Don't leave it ambiguous.
2. **What's already aligned?** List the files/components that the
   design wants and that already exist correctly. These do not need
   work and must not be rebuilt.
3. **What violates the new doctrine?** List the exact files/symbols
   that must be excised. This becomes the deletion target across
   later steps.

The pre-flight is small but load-bearing — it determines whether the
plan is a migration sequence or a build sequence.

### Phase 2: Extract properties from the design

Walk the design's doctrine section. For each non-negotiable, write a
property:

```
### P<n> — <name>

**Invariant:** <one-line statement of what must always be true>
**Forbids:** <concrete things that cannot exist in the codebase>
**Allowed:** <distinguish legitimate cases that look forbidden>
**Proved by:** <which step + which test enforces this>
```

Calibration:

- **Aim for 5–8 properties.** Fewer = you're missing invariants.
  More = you're conflating taste with non-negotiables.
- **Every property is testable.** If it can't be expressed as a
  pytest/vitest/grep, it's not a property — it's a vibe.
- **Properties are tied to steps.** Each one names the step that
  introduces its test. If no step proves it, either add the test or
  drop the property.
- **Add properties the design implies but doesn't state.** Common
  additions: reproducibility (same inputs → byte-identical outputs),
  plugin isolation (adding one component doesn't change another's
  output), schema-is-only-contract (typed access, no `as any`).

### Phase 3: Identify vertical slices

A **vertical slice** lands one capability end-to-end:

```
producer logic → schema field → artifact → consumer reads → user sees
```

For a producer/consumer system (the most common shape):

- **One derived quantity per slice.** Not "all extractors first, then
  all consumer wiring later" — that's horizontal, and the midstream
  is unverifiable.
- **Each slice usually deletes something AND adds something.** The
  deletion is *gated* by the addition working (delete-after-verify).
- **The first slice is the simplest extractor.** It proves the pattern
  with low complexity. The second slice is the most complex extractor
  with the most invariants. Together they prove the doctrine works
  for both trivial and complex cases.

Anti-pattern: a "Stage 2: build all extractors" mega-step. Always
split per quantity.

### Phase 4: Sequence the steps

Standard shape for a producer/consumer rewrite:

```
Step 0 — Foundation (test harness, CI, package skeleton)
Step 1 — Lock the contract (schema/types + a stub that proves
         pluggability)
Step 2 — First vertical slice (simplest extractor end-to-end)
Step 3 — Second vertical slice (most complex extractor)
Step 4 — Remaining extractors + consumer wiring + slim
         legacy artifacts
Step 5 — CI guards + failure-injection tests
Step 6 — Heavy independent piece (e.g. infrastructure swap)
Step 7 — Observability
Step 8 — Optional extensions
```

Critical path: **0 → 1 → {2, 3} → 4 → 5**. Steps 6, 7, 8 are
independent and can be done in parallel.

**Ordering rules:**

- **CI guards (Step 5) come *after* the violations are gone**
  (Steps 2, 3). Otherwise main goes red on merge.
- **Heavy infra work (Step 6) is parallel.** Doesn't block the SPA
  work; can ship anytime after Step 1.
- **Tests for an abstraction live with the step that builds the
  abstraction.** This is the bug we caught — property tests cannot
  reference `EXTRACTORS` in Step 0 because that abstraction doesn't
  exist until Step 1. See §"Common pitfalls" below.

Always include a dependency diagram in the doc:

```
0 ──▶ 1 ─┬─▶ 2 ─┐
         ├─▶ 3 ─┼─▶ 4 ──▶ 5
         ├─▶ 6 ◀┘
         ├─▶ 7
         └─▶ 8
```

### Phase 5: Write per-step contracts

Every step has the same shape — make this consistent across the doc:

```markdown
## Step N — Title

**Goal:** one sentence.
**Why now:** what doesn't work without this; why this position in
the order.
**Note:** any ordering caveat (e.g., "this test requires the
abstraction in Step M; that's why it lives here, not earlier").

### Tests first
- [ ] test file + the invariants it asserts (bulleted).

### Implementation
- [ ] minimum code to satisfy the tests.

### Integration check
- [ ] golden-path test green (§A).
- [ ] manual verification, if applicable.

### Acceptance
- [ ] binary checks proving doneness (greps that return empty,
      versions bumped, files deleted, screenshots equal, etc.).

**Depends on:** prior step numbers.
```

Per-step rules:

- **Tests-first is structural.** The "Tests first" block always
  precedes "Implementation." Coding agents must complete tests
  before touching the impl.
- **Acceptance is binary.** A checkbox is checkable or not. No
  "mostly done." A grep that returns empty is the strongest possible
  acceptance gate.
- **Deletions live in Acceptance, not in Implementation.** This
  enforces delete-after-verify: the impl block adds the replacement;
  the acceptance block (gated by tests passing) is where the old
  code is removed.

### Phase 6: Add cross-cutting tests

Two test layers serve different purposes:

**The golden-path integration test (§A) is the spine.** One fixed
input → one stamped expected output. Runs after every step. If it
goes red, the most recent step caused it.

```
GIVEN  a fixed fixture (e.g. one demo element)
WHEN   the full pipeline runs with current code + versions
THEN   the resulting artifact matches a stamped golden file
       byte-for-byte after canonicalization
AND    the consumer (e.g. SPA) mounts and renders without error
AND    every capability present at this step shows real values
```

Golden file is updated **only** at the end of steps that intentionally
change the artifact's content. Mid-step updates are a red flag.

**Property tests** prove each P<n> invariant:

| Property | Test pattern |
|---|---|
| Statelessness | run any pure function twice, assert byte-identical output |
| Idempotence | run full pipeline twice, assert byte-identical artifact + cache hit on second run |
| Pluggability | register a stub component, verify it lands in the artifact without touching dispatchers |
| Plugin isolation | run with N components, run with N-1, assert the N-1 surviving outputs are byte-identical |
| Fail visibly | inject component-that-throws / NaN-emitting input / missing field, assert visible failure (named error path, not silent fallback) |
| Schema-only-contract | grep for `as any` or untyped JSON access in consumer paths |

### Phase 7: Surface design tensions

Every design has unresolved tensions. **Don't silently resolve them
in the plan** — that buries decisions a human should make. Add an
appendix `§D — Design tensions surfaced for review` with:

```
**D<n>. <name>.**

<one-paragraph statement of the tension>

Options:
- (a) <option> — <tradeoff>
- (b) <option> — <tradeoff>

Recommendation: <choice + reasoning>
```

Common tensions worth surfacing:

- **"One canonical artifact" vs. companion files.** Distinguish
  derived-data artifacts from presentation/visual companions.
- **"Fully modular" components that share inputs.** Document the
  legitimate couplings (e.g., one extractor reading another's slice
  via registry ordering).
- **Inlined vs. split components.** When does the registry file split
  into per-component files.
- **Unused escape hatches** in the design — if a field/path isn't
  exercised by any step, flag for removal.

---

## Operating principles for the plan itself

These bake into the deliverable so coding agents follow them:

1. **Contract first.** Step 1 always locks the schema/types. Nothing
   else starts until both compile.
2. **One quantity, end-to-end per step.** Not horizontal layers.
3. **Rewrite from scratch when easier — but verify before deleting.**
   The gate is the test passing, not whether the new code was
   *ported* or *rewritten*. A 50-line clean rewrite beats a 200-line
   preserved-from-history port. Mention the chosen path in the PR
   body so reviewers know which kind of change to read.
4. **A failing test is information.** Read the assertion. Decide if
   the test or the impl is wrong before fixing.
5. **No scope creep to escape a stuck step.** Follow the iteration
   loop. A wholesale rewrite of one file is a valid escape — not
   scope creep.
6. **Idempotent re-runs.** Every script + every CI step safe to run
   twice.
7. **Pin and stamp.** Every artifact stamps its versions. Every
   golden file is committed alongside the code that produced it.
8. **Properties are merge gates.** A step that demonstrably weakens
   a property cannot merge.

---

## The iteration loop (bake this into the plan as §B)

```
   Read failing assertion verbatim
        │
        ▼
   Is the test's invariant correct?
        │
   No ◀─┴─▶ Yes
   │        │
   ▼        ▼
   Fix     Fix impl
   test    (minimum change OR rewrite the file fresh —
   +       whichever is faster against the test)
   PR
   note    │
        ▼
   Re-run failing test → run golden path → green ⇒ done
```

**Stuck >30 min on the same failure:**

1. Stop coding. Write expected vs. observed in the PR draft.
2. Print actual values. Then fix or revert the print.
3. Re-read the step's Acceptance block — solving the right problem?
4. **Consider rewriting the file from scratch.** If the stuck thing
   is one component, starting fresh against the acceptance test is
   often faster than untangling.
5. If still stuck, escalate in the PR description. Do **not** start
   the next step.

---

## Common pitfalls (and how to avoid them)

### Pitfall 1: Property tests reference abstractions that don't exist yet

**Symptom:** Step 0 has a "test_statelessness for every extractor in
EXTRACTORS" test — but `EXTRACTORS` is defined in Step 1.

**Fix:** **Tests live with the step that introduces the abstraction
they test.** Step 0 ships test infrastructure only. Property tests
land alongside the code they exercise:

- Schema round-trip → Step 1 (when schema exists)
- Statelessness → Step 1 (when the protocol + a stub exist)
- Pluggability → Step 1 (same)
- Idempotence (full bake) → Step 2 (first real end-to-end pipeline)
- Plugin isolation → the step where the Nth component lands
- Failure injection → after the failure modes are real (typically
  Step 5)

The principle: a property test must run against *something*. Build
the smallest abstraction needed alongside the test.

### Pitfall 2: Horizontal slicing leaks in via "build all the extractors first"

**Symptom:** Step 2 says "build PhasesExtractor, SummaryExtractor,
AxisExtractor, EffortExtractor" in one step.

**Fix:** Split per extractor as separate vertical slices. Each slice
ends with the consumer rendering the new field. Anything else is
horizontal.

### Pitfall 3: Acceptance gates are soft

**Symptom:** "Done when the demo looks right."

**Fix:** Replace with a grep that must return empty, a test that
must pass, a version that must be bumped, or a file that must be
deleted. Binary or it isn't acceptance.

### Pitfall 4: Defensive prose explaining what won't be built

**Symptom:** Long "anti-patterns" / "what we explicitly do NOT build"
lists scattered throughout each step.

**Fix:** Defensive content goes in **one** appendix (`§C — Out of
scope`). Per-step content is what to build, not what not to.

### Pitfall 5: Screenshot-diff for "visual parity"

**Symptom:** A step's acceptance says "screenshot looks identical to
before."

**Fix:** Assert the *values* you care about. For an SVG overlay,
extract the `<line>`/`<path>` attributes and assert they match a
stamped baseline within float tolerance. This catches drift; pixel
diff doesn't and is brittle to anti-aliasing.

### Pitfall 6: The plan recommends migrate when rewrite is easier (or vice versa)

**Symptom:** The Phase 1 recommendation is unjustified or defaults
to "migrate" without examining the codebase.

**Fix:** State the *recommendation*, the *reasoning*, AND **defer to
the user** if uncertain. Don't paper over the choice.

### Pitfall 7: Properties are aspirations, not gates

**Symptom:** "The system should be modular" appears in the doctrine
but no test enforces it.

**Fix:** Every property has a test in a specific step. If no test
exists, the property is fiction — either add the test or remove the
property.

---

## Quality gates for the plan itself

Before declaring `IMPLEMENTATION_PLAN.md` ready for execution, verify:

- [ ] Top-of-doc has a 30-second readable "Steps at a glance"
      checklist.
- [ ] Every step is a top-level `## Step N — Title` heading.
- [ ] Every step has all six sub-blocks: Goal, Why now, Tests first,
      Implementation, Integration check, Acceptance, Depends on.
- [ ] Every property (P1, P2, …) is tied to a specific step + test.
- [ ] No property test references an abstraction that doesn't exist
      yet at its step.
- [ ] Step 0 ships test infrastructure only — no property tests with
      forward references.
- [ ] Acceptance gates are binary (grep empty / test green / file
      deleted / version bumped).
- [ ] Vertical slicing is preserved — no "build all X" mega-steps.
- [ ] Critical path and parallelizable steps are explicit.
- [ ] Golden-path integration test (§A) is defined.
- [ ] Iteration loop (§B) is in the doc, not just in the agent's
      head.
- [ ] Out-of-scope appendix (§C) lists what the plan does NOT build.
- [ ] Design tensions (§D) are surfaced, not silently resolved.
- [ ] Rewrite-from-scratch is allowed in the operating principles
      and in the stuck protocol.
- [ ] First step has no forward dependencies. If your "Step 1" needs
      something from Step 3, the ordering is wrong.

---

## When to iterate the plan with the user

The first draft is rarely final. Common feedback loops:

- **"Make the steps more visible."** → Restructure so `## Step N`
  headings dominate; demote meta-content to appendices.
- **"This is too long / too defensive."** → Cut "what we won't build"
  prose; consolidate into §C.
- **"What if rewriting is easier than migrating?"** → Add the
  rewrite-from-scratch principle and weave it into the stuck
  protocol.
- **"What's the first step?"** → If the user has to ask, the
  "Steps at a glance" checklist isn't doing its job. Tighten it.
- **"Wait, doesn't step X depend on something not built yet?"** →
  You hit Pitfall 1. Move the test to where the abstraction
  exists.

Iteration is normal. The skill is delivering a plan that *gets to*
ready, not pretending the first pass is.

---

## Reference

- [reference/IMPLEMENTATION_PLAN_TEMPLATE.md](reference/IMPLEMENTATION_PLAN_TEMPLATE.md) —
  full template for the deliverable, ready to fill in.
