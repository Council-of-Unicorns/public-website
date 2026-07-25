# IMPLEMENTATION_PLAN.md — execution checklist

> Companion to [`<DESIGN_DOC>.md`](./<DESIGN_DOC>.md). That document is
> **what** the system is. This one is **how to land it** — the steps,
> the tests that gate each one, the loop when something fails, and
> the binary acceptance for each.
>
> **Status: ready to execute.**

---

## The steps at a glance

The system ships in **N steps**. Each is one PR. Each ends with a
binary acceptance check and the golden-path test (§A) green.

- [ ] **Step 0** — Foundation: <tool / harness / package skeleton>
- [ ] **Step 1** — Lock the contract: <schema + typed mirror>
- [ ] **Step 2** — First vertical slice: <simplest capability>
- [ ] **Step 3** — Second vertical slice: <complex capability>
- [ ] **Step 4** — <remaining capabilities + consumer wiring>
- [ ] **Step 5** — CI guards + failure-injection tests
- [ ] **Step 6** — <independent heavy piece>
- [ ] **Step 7** — Observability
- [ ] **Step 8** — (optional) <extension>

Critical path: **0 → 1 → {2, 3} → 4 → 5**. Steps **6, 7, 8** are
independent of the critical path and can run in parallel.

```
0 ──▶ 1 ─┬─▶ 2 ─┐
         ├─▶ 3 ─┼─▶ 4 ──▶ 5
         ├─▶ 6 ◀┘
         ├─▶ 7
         └─▶ 8
```

---

## Properties the system must preserve

These are the invariants every step is judged against. A step that
weakens any of them **cannot merge** without explicit reviewed
justification.

### P1 — <name>

**Invariant:** <one-line statement>
**Forbids:** <concrete patterns that cannot exist>
**Allowed:** <legitimate cases that look similar>
**Proved by:** <step + test>

### P2 — <name>
…

(Aim for 5–8 properties. Every one tied to a measurable test. See
the skill's Phase 2 for calibration.)

---

## How to execute (read once before starting)

- **Steps are vertical slices.** Each lands one capability end-to-end.
  Never horizontal-slice.
- **Tests first.** Each step has a "Write tests first" block.
  Complete it before touching implementation.
- **Each step ends with a binary acceptance check.** No soft-passes.
- **The golden-path test (§A) runs after every step.** Red ⇒ the
  most recent step caused it.
- **Rewrite from scratch when it's easier.** The acceptance gate is
  the test passing, not whether the new code was *carefully ported*
  or *thrown away and rewritten*. Pick whichever is faster against
  the test. Mention the chosen path in the PR body.
- **No scope creep to escape a stuck step.** Use the loop in §B.

---

## Step 0 — Foundation

**Goal:** stand up the test harness, CI, and package scaffolding so
every later step has somewhere to land.

**Why first:** without a running test harness, every later test is
hope-not-prove.

**Note:** Step 0 ships *test infrastructure only*. Property tests
that reference abstractions (`EXTRACTORS`, `run_batch.py`, etc.)
land in later steps alongside the code they test.

### Tests first
- [ ] `<smoke test>` — proves the harness runs.

### Implementation
- [ ] <package skeleton>
- [ ] <dependencies>
- [ ] <CI job>
- [ ] <build integration, if any>

### Integration check
- [ ] CI green on a no-op PR.
- [ ] <build command> succeeds locally.

### Acceptance
- [ ] Smoke test passes.
- [ ] CI runs the test target on a real PR.
- [ ] No regression in existing CI.

**Depends on:** nothing.

---

## Step 1 — Lock the contract

**Goal:** the schema is real, versioned, and round-trips between the
producer language and the consumer language. A stub component proves
the plug-in path.

### Tests first
- [ ] `<schema round-trip test>` — load fixture through the
      schema, re-serialize, byte-identical.
- [ ] `<pluggability test>` — stub component lands its slice in
      the artifact without touching any dispatcher.
- [ ] `<statelessness test>` — for every component in the registry,
      calling its function twice on identical inputs yields
      byte-identical output. Runs once now with the stub;
      automatically covers every future component.
- [ ] `<typed-import test>` — consumer-side type compile against
      the same fixture.

### Implementation
- [ ] `<schema file>` — write fresh from the design's spec.
- [ ] `<fixture artifact>` — hand-built sample.
- [ ] `<registry runner>` — minimum loop over registered components.
- [ ] `<consumer types>` — hand-mirror of the schema.

### Acceptance
- [ ] All four test files green.
- [ ] Schema files are field-for-field equivalent on the two sides.

**Depends on:** Step 0.

---

## Step 2 — First vertical slice: <simplest capability>

**Goal:** the simplest capability flows producer → schema → artifact
→ consumer. Any existing duplicate implementation on the consumer
side is deleted.

**Why first:** the simplest capability proves the pattern with the
lowest complexity. If the same quantity exists on both sides today,
this is the highest-risk drift bug and removing it first is the
biggest doctrine win per unit work.

### Tests first
- [ ] `<invariant tests>` — domain invariants for this quantity.
- [ ] `<snapshot test>` — output for a fixture matches stamped
      expected.
- [ ] `<idempotence test>` (first runnable here, because the full
      pipeline now exists): run twice → byte-identical artifact +
      cache hit on second run.

### Implementation
- [ ] `<producer extractor>` — write fresh from the spec.
- [ ] `<consumer loader>` — typed fetch + integration with the
      consumer's dispatcher.
- [ ] Bake one fixture end-to-end; commit the resulting artifact.
- [ ] `<consumer overlay/render>` — read from the artifact; delete
      any duplicate computation.

### Integration check
- [ ] `<render parity test>` — render the overlay; assert SVG/value
      attributes match a stamped pre-stage baseline within tolerance.
- [ ] Manual: open the demo, look correct.
- [ ] Golden-path test (§A) — created in this step; commit it.

### Acceptance
- [ ] `<grep for the deleted pattern>` returns empty.
- [ ] All tests green.
- [ ] Schema version bumped.

**Depends on:** Step 1.

---

## Step 3 — Second vertical slice: <complex capability>

(Same shape as Step 2. Choose the most complex capability with the
most encoded invariants; this proves the doctrine for hard cases.)

---

## Step 4 — <remaining capabilities + consumer wiring + slim
legacy>

(Add remaining extractors. Turn placeholder consumer surfaces into
live reads. Slim down any legacy artifact to its narrowest shape.
Add isolation + swap-out tests here.)

### Tests added here
- [ ] `<isolation test>` (P6) — bake with N components, bake with
      N-1, surviving outputs byte-identical.
- [ ] `<swap-out test>` (P2 modular swap) — disabling one component
      shows "feature unavailable" for its UI; the rest render fine.

---

## Step 5 — CI guards + failure-injection tests

**Goal:** every property is mechanically enforced. PRs that weaken
them fail CI. Failure modes are explicitly tested.

### Tests first (failure injection — pin P4)
- [ ] `<component-that-throws>` — bake survives; affected fields
      `null`; error logged.
- [ ] `<bad-input-fails-fast>` — corrupt input fails the bake with
      a clear diagnostic. No partial artifact written.
- [ ] `<missing-field-on-consumer>` — consumer renders "unavailable"
      affordance; no throw, no recompute.

### Implementation (guards)
- [ ] `<grep for forbidden patterns under consumer paths>` → fail.
- [ ] `<schema-version bump rule>` — if extractor changed, version
      bumped.
- [ ] `<typed-access rule>` — no `as any` on artifact paths.

### Integration check
- [ ] Synthetic PRs that violate each guard go red; reverts go green.

---

## Step 6 — <independent heavy piece>

(e.g., infrastructure swap. Independent of the critical path; can
run in parallel.)

---

## Step 7 — Observability

(Instrumentation + the small set of metrics declared in the design.
Commit baseline numbers.)

---

## Step 8 — (optional) <extension>

(Extension that locks a future path open without committing to it,
e.g. a Dataset wrapper for future training. Defer if not needed.)

---

## Definition of done (whole plan)

All of the following must be true:

- [ ] **Steps 0–7 acceptance fully checked.** Step 8 done or
      explicitly deferred.
- [ ] **P1:** <grep / test that proves it>
- [ ] **P2:** pluggability + isolation + swap-out tests green.
- [ ] **P3:** <artifact-singularity check>
- [ ] **P4:** all failure-injection tests green.
- [ ] **P5:** re-running the pipeline hits the cache (zero work).
- [ ] **P6:** isolation test green.
- [ ] **P7:** typed-access grep clean.
- [ ] Observability metrics emit; baseline committed.
- [ ] All CI guards live.
- [ ] §A golden path green.
- [ ] Deployment still works.

---

## §A — The integration test (golden path)

Lives at `<path>`.

```
GIVEN  a fixed fixture (one demo element from the committed corpus)
WHEN   the full pipeline runs with current code + versions
THEN   the resulting artifact matches a stamped golden file
       byte-for-byte after canonicalization
AND    the consumer mounts and renders without error
AND    every capability present at this step shows real values
```

Golden file: `<path>`. Updated **only** at the end of steps that
intentionally change artifact content. Mid-step updates are a red
flag.

---

## §B — Iteration loop (when something fails)

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
   test    (minimum change OR rewrite the file fresh)
   +
   PR
   note
        ▼
   Re-run failing test → run §A → green ⇒ done
```

**Stuck >30 min on the same failure:**

1. Stop coding. Expected vs. observed in PR draft.
2. Print actual values; fix or revert the print.
3. Re-read the step's Acceptance block.
4. **Consider rewriting the file from scratch.** Test is your spec.
5. Escalate in PR description. Do not start the next step.

---

## §C — Out of scope (do not build)

If a step's work creeps into any of these, **stop and re-scope**:

- <future extension #1>
- <future extension #2>
- <distributed infra, scaling, multi-region — v2 problems>
- <backwards-compat shims for the legacy artifact>

---

## §D — Design tensions surfaced for review

These are tensions worth resolving explicitly before <step X> ships.
Flag in early PRs; resolve in the relevant step's PR at the latest.

**D1. <name>.**

<one-paragraph statement>

Options:
- (a) <option> — <tradeoff>
- (b) <option> — <tradeoff>

Recommendation: <choice + reasoning>

**D2. <name>.** …

---

*Plan compiled <date>. To be marked complete one step at a time,
in order, with §A green between steps. PRs reference the property
(P<n>) they advance.*
