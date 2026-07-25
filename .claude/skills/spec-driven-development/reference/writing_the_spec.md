# Writing the Spec

Covers the anatomy of a usable, executable specification — the document from which code and tests are derived. Load this when starting any spec-first task, before writing code or tests.

## Doctrine

A spec makes success **binary**. Every acceptance criterion is something a test can pass or fail — no judgment call required. **Vague criteria are bugs in the spec**, fix them before writing code. If you cannot imagine the assertion, the criterion is not done.

| When to use | When to avoid |
| --- | --- |
| Ambiguous, multi-file, or multi-pass work | One-line fixes with an obvious diff |
| Behavior must be agreed before implementation | Throwaway spikes you will delete |
| Code + tests will be derived and traced back | Pure refactors with existing test coverage |
| Requirements likely to change under you | Trivial CRUD with a known shape |

## What a Spec Contains

| Section | Content | Rule |
| --- | --- | --- |
| Goal | One sentence: what success looks like | Exactly one sentence |
| In-scope | Bulleted, explicit | What this delivers |
| Out-of-scope | Bulleted, explicit | What it deliberately does NOT do |
| Requirements | EARS statements | One behavior per line |
| Acceptance criteria | Binary, ID'd (AC-N) | Each maps to a test |
| Invariants | Always-true properties | Candidates for property tests |
| Failure semantics | Error codes, retries, partial-failure behavior | Per failure mode |
| Non-functional | perf / security / limits | Numbers, not adjectives |
| Open questions | Unresolved decisions | Must be empty before coding |
| Dependencies / assumptions | External systems, preconditions | State them or they bite you |

## EARS Requirement Syntax

EARS (Easy Approach to Requirements Syntax) gives each requirement a clause structure that forces a trigger and a single behavior.

| Pattern | Template | Example |
| --- | --- | --- |
| Ubiquitous | The system shall ... | The system shall store passwords hashed with Argon2id. |
| Event-driven | WHEN `<trigger>` the system shall ... | WHEN a user submits the form the system shall validate all fields before persisting. |
| State-driven | WHILE `<state>` the system shall ... | WHILE a sync is in progress the system shall reject new sync requests with 409. |
| Unwanted behavior | IF `<condition>` THEN the system shall ... | IF the email is malformed THEN the system shall return 422 with a field-level error. |
| Optional feature | WHERE `<feature included>` the system shall ... | WHERE rate limiting is enabled the system shall reject the 101st request per minute with 429. |

**Good vs bad:**

```text
BAD:  The system should handle errors gracefully.
GOOD: IF the upstream returns 5xx THEN the system shall retry 3x with exponential backoff,
      then return 503 with Retry-After.

BAD:  Logins should be fast and secure.
GOOD: WHEN valid credentials are submitted the system shall issue a session token within 200ms (p99).
```

## Binary Acceptance Criteria

Give every criterion a **stable ID** (AC-1, AC-2, …) so tests can reference it and survive renumbering.

| Avoid (unverifiable) | Prefer (testable) |
| --- | --- |
| "Login is fast" | AC-1: p99 latency < 200ms at 1k rps over a 60s run |
| "Handles bad input well" | AC-2: invalid email returns 422 with `{field, message}` per error |
| "Should scale" | AC-3: sustains 10k concurrent connections, < 1% error rate |
| "Secure password storage" | AC-4: stored hash matches `^\$argon2id\$`; plaintext never logged |
| "Idempotent" | AC-5: same Idempotency-Key returns the original response, no second write |

Each AC is one observable fact. If it needs "and", split it.

## Spec Template

```markdown
# Spec: <feature name>

## Goal
<one sentence>

## Scope
In:  - <bullet>  - <bullet>
Out: - <bullet>  - <bullet>

## Requirements (EARS)
- R1 (ubiquitous):  The system shall ...
- R2 (event):       WHEN ... the system shall ...
- R3 (unwanted):    IF ... THEN the system shall ...

## Acceptance Criteria
- AC-1: <binary, observable>
- AC-2: <binary, observable>
- AC-3: <binary, observable>

## Invariants
- INV-1: <always-true property>

## Failure Semantics
- <failure mode> -> <status/behavior/side-effects>

## Non-Functional
- Perf:     <number + load>
- Security: <concrete requirement>
- Limits:   <max sizes, rates, timeouts>

## Open Questions
- [ ] <question> (owner, due)

## Dependencies / Assumptions
- <external system / precondition>
```

## Anti-Patterns

| Anti-pattern | Why it fails | Fix |
| --- | --- | --- |
| Criterion restates the implementation ("calls `saveUser()`") | Couples spec to code; can't change impl | Assert observable behavior, not internals |
| Missing failure / edge cases | Tests only cover happy path; bugs ship | Add IF/THEN requirements per failure mode |
| No Out-of-scope section | Scope creep; reviewers disagree silently | List what you deliberately exclude |
| No Open Questions block | Ambiguity gets guessed at during coding | Force unknowns to the surface; resolve first |
| Success you can't check | "Works well" — no possible assertion | Rewrite until a test can pass/fail it |
| Acceptance criteria without IDs | Tests can't trace; renumbering breaks links | Assign AC-N stable IDs |

## "Spec Is Executable Yet?" Checklist

- [ ] Goal is a single sentence.
- [ ] In-scope AND out-of-scope are both explicit.
- [ ] Every requirement uses an EARS pattern (one behavior per line).
- [ ] Every acceptance criterion is binary and has a stable ID.
- [ ] No criterion restates implementation detail.
- [ ] Failure semantics exist for each failure mode (not just happy path).
- [ ] Non-functional requirements carry numbers, not adjectives.
- [ ] Invariants are listed (property-test candidates).
- [ ] Open Questions block is present and **empty**.
- [ ] Dependencies and assumptions are stated.

## Verification

Run these before declaring the spec ready and before writing code:

```bash
# 1. Every acceptance criterion has an ID.
grep -nE '^\s*-?\s*AC-[0-9]+' spec.md

# 2. No open questions remain (must print nothing).
grep -nE '^\s*-\s*\[ \]' spec.md && echo "UNRESOLVED — do not code yet"

# 3. Each AC ID is traceable to a test (every ID should appear in tests/).
for id in $(grep -oE 'AC-[0-9]+' spec.md | sort -u); do
  printf '%s: ' "$id"; grep -rl "$id" tests/ || echo "NO TEST"
done

# 4. Requirements use EARS markers.
grep -cE 'shall|WHEN|WHILE|IF .* THEN|WHERE' spec.md
```

Look for: every AC-N resolves to at least one test file; the open-questions grep is empty; requirements use `shall` / `WHEN` / `IF…THEN`. Resolve all open questions before coding.

References: EARS (Mavin et al.) for requirement syntax; GitHub Spec Kit for spec-driven tooling and templates.

Next: derive code and tests from these IDs — see [deriving_code_and_tests.md](deriving_code_and_tests.md) — and keep the spec in sync as requirements move — see [keeping_specs_authoritative.md](keeping_specs_authoritative.md).
