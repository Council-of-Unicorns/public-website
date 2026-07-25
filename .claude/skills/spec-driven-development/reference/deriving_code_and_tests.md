# Deriving Code and Tests from a Locked Spec

Covers turning a locked spec into work — code and tests — without drift, via a traceability matrix, AC-derived test cases, and vertical slices. Load this once the spec is written (see [writing_the_spec.md](writing_the_spec.md)) and you're about to implement or hand the work to a coding agent.

## Doctrine

> Every change traces to a requirement. Every test is derived from an acceptance criterion — never reverse-engineered from the code you wrote.

- **Spec → tests → code.** Tests come from acceptance criteria (ACs) *before* the implementation exists. A test written by reading the finished code only proves the code does what it does, not what was required.
- **An AC with no test is unbuilt.** Coverage is not "the code looks done"; it is "the criterion has a failing-then-passing test."
- **Code with no AC is scope creep.** If a module maps to no requirement, either the spec is missing a requirement (add it — see [keeping_specs_authoritative.md](keeping_specs_authoritative.md)) or the code shouldn't exist.
- **Thin and end-to-end beats broad and layered.** Ship a vertical slice that's verifiable today, not a horizontal layer that verifies nothing until the end.

## When to use / avoid

| Use | Avoid / skip |
|---|---|
| Spec is locked and has stable AC IDs | Spec still has open questions — resolve them first |
| Multi-file or agent-driven work | Trivial one-liner with an obvious single test |
| Work will be handed to a coding agent | Spike/throwaway prototype you will delete |
| You need to *prove* coverage to a reviewer | — |

## The traceability matrix — the coverage contract

One markdown table is the contract that proves the spec is built and nothing extra is. Keep it next to the spec.

| Req/AC ID | Acceptance criterion (short) | Test(s) | Code module | Status |
|---|---|---|---|---|
| AC-1 | Reject withdrawal > balance | `test_withdraw_overdraft` | `account.withdraw` | green |
| AC-2 | Withdrawal at exact balance succeeds, leaves 0 | `test_withdraw_to_zero` | `account.withdraw` | green |
| AC-3 | Balance never goes negative (invariant) | `test_balance_nonneg_property` | `account.withdraw` | red |
| AC-4 | Concurrent withdrawals don't double-spend | `test_withdraw_concurrent` | `account.withdraw`, `ledger.lock` | todo |

Read it two ways, both mandatory:

- **Every AC row has a Test and a Code module.** A blank Test cell = unbuilt. A row stuck at `red`/`todo` = not done.
- **Every Code module appears against some AC.** A module with no AC = scope creep; justify it (add a requirement) or delete it.

`Status` values: `todo` → `red` (test exists, fails) → `green` (passes). The matrix is done when every AC row is `green` and no module is orphaned.

## Deriving test cases from one acceptance criterion

For **every** AC, enumerate four buckets — don't stop at the happy path:

1. **Happy path** — the criterion met under normal input.
2. **Boundaries** — the edges: empty, zero, max, off-by-one, exact-equal.
3. **Failure modes** — invalid input, missing data, downstream error, contention.
4. **Invariant preserved** — the property that must hold *across* all of the above (often a property-based test).

### Worked example

> **AC-1:** A withdrawal of amount `a` from an account with balance `b` succeeds iff `0 < a <= b`; on success the new balance is `b - a`; the balance is never negative.

| Bucket | Test case |
|---|---|
| Happy | `a=30, b=100` → succeeds, balance `70` |
| Boundary | `a == b` (e.g. `100/100`) → succeeds, balance `0` |
| Boundary | `a = b + 1` → rejected, balance unchanged |
| Failure | `a = 0` and `a < 0` → rejected (`ValueError`), balance unchanged |
| Failure | account not found → rejected, no mutation |
| Invariant | for all `(a, b)`: after `withdraw`, `balance >= 0` and `balance ∈ {b, b-a}` (property test) |

One AC fans out to ~6 test cases. That fan-out is the point — it's where the spec's true surface area becomes visible.

## Vertical slicing

Cut the spec into thin end-to-end increments, each independently shippable and independently verifiable. Each slice carries its own AC IDs, code, and tests through to green before the next starts.

| Prefer — vertical slice | Avoid — horizontal layers |
|---|---|
| "Withdraw one account, end to end" (API → domain → store → test) | "All ORM models," then "all services," then "all endpoints" |
| Something demoable / testable after each slice | Nothing runs until the final layer lands |
| Integration risk surfaces on day 1 | Integration risk hides until the end |
| Each slice maps to a contiguous set of AC rows that go green | ACs span all layers; none can go green until everything exists |
| Easy to reorder, drop, or reprioritize a slice | Layers are entangled; cutting scope means rework |

Slice along **user-visible behavior / AC clusters**, not along architectural tiers.

## Handing the spec to a coding agent

The spec **plus** the traceability matrix **is** the prompt contract. The agent's job is to make the ACs pass and not exceed scope. Tests are produced via the `test-driven-verification` skill — load that skill for the red-green loop and evidence capture; this matrix tells it which ACs to derive from.

A handoff prompt must include:

- [ ] The relevant **AC IDs** verbatim, with their exact criteria.
- [ ] The **invariants** that must hold across all changes.
- [ ] The **out-of-scope** list — what the agent must *not* touch or build.
- [ ] The instruction: *make these ACs pass, write the tests first, do not implement beyond these ACs.*
- [ ] The matrix rows to fill (`Test`, `Code module`, `Status`) as proof of work.

If the agent wants to build something with no AC, that's a spec conversation, not a coding decision — bounce it back to the spec.

## Anti-patterns

- **Tautological tests** — writing the test after, and from, the implementation. It asserts the code's current behavior, not the requirement. Smell: the test changed in the same commit as the code, "to match."
- **Gold-plating past the spec** — extra config, hooks, "while I'm here" features with no AC. Every line should trace to a row.
- **Broad horizontal builds** — all models, then all endpoints; nothing verifiable until the last layer. No green ACs for days.
- **Lost AC→test link** — tests exist but nobody can say which AC each covers; the matrix rots; coverage becomes a guess.
- **Vague AC carried into code** — if the AC isn't binary, the test can't be either. Fix the spec first.

## Checklist

**Before coding a slice:**

- [ ] Spec is locked; the slice's AC IDs are stable and binary.
- [ ] Each AC has rows in the matrix; tests enumerated across happy / boundary / failure / invariant.
- [ ] Tests written and **red** before implementation (via `test-driven-verification`).
- [ ] Slice is vertical and independently shippable; out-of-scope is explicit.

**Before calling a slice done:**

- [ ] Every AC in the slice is **green** in the matrix.
- [ ] Every new/changed module traces to an AC — no orphans.
- [ ] Each AC ID appears in at least one test (grep below).
- [ ] No code added beyond the slice's ACs.
- [ ] Matrix committed alongside the code.

## Verification

```bash
# 1. Every AC referenced in the spec appears in a test (catch missing coverage).
grep -roE 'AC-[0-9]+' spec.md | sort -u           > /tmp/ac_spec.txt
grep -roE 'AC-[0-9]+' tests/   | sort -u           > /tmp/ac_tests.txt
comm -23 /tmp/ac_spec.txt /tmp/ac_tests.txt        # ACs with NO test → must be empty

# 2. Every AC in the matrix is green (no todo/red left).
grep -E '^\| AC-' traceability.md | grep -vE 'green' # → must be empty when done

# 3. Coverage of the actual code (proves modules are exercised).
pytest --cov=src --cov-report=term-missing          # Python
# go test ./... -cover ; cargo llvm-cov ; jest --coverage   # other stacks

# 4. No un-spec'd modules: list source modules, diff against the matrix's Code column.
#    Anything in src/ not named in the matrix = scope creep to justify or delete.
```

What to look for:

- **Step 1 output empty** — no orphan ACs (every criterion is tested).
- **Step 2 output empty** — every AC row is `green`.
- **Step 3** — modules tied to ACs have meaningful coverage; uncovered lines map to an AC or shouldn't exist.
- **Step 4** — no source module is absent from the matrix (no scope creep).

Run steps 1, 2, and 4 in CI so a new untested AC, a non-green row, or an un-spec'd module fails the build. For the red-green loop and evidence capture that produce these tests, load the `test-driven-verification` skill. When verification reveals the spec itself was wrong, stop and fix the spec first — see [keeping_specs_authoritative.md](keeping_specs_authoritative.md).
