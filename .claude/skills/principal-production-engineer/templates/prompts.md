# Prompt Templates

Drop-in prompts for steering a coding agent against this skill.

## Plan-first for complex work

```text
Use the strategic-engineering-planner skill.

Task: [describe the system / change].

Produce the full planning output (Goal, Success Metrics, Constraints, Non-Goals,
Requirement Audit, Existing System Understanding, Architecture Decomposition,
Core Entities and Interfaces, Data Flow / Control Flow, State Machines,
Architecture Options, Tradeoff Analysis, Risks and Bottlenecks, Invariants,
Vertical Slice Strategy, Milestone Roadmap, Verification Strategy,
Deferred Complexity, Recommended Next Step, Open Questions).

Stop after the roadmap. Wait for review before implementing.
```

## Implement production component

```text
Use the principal-production-engineer skill.

Implement [component/change].

Requirements:
- [functional]
- [performance]
- [safety/reliability]

Constraints:
- simple, direct code; minimal abstraction
- explicit ownership; no hidden allocation in hot path; no hidden throwing
- in C++: [[nodiscard]] bool noexcept for simple expected failure;
  Result<T, E> noexcept when failure reason matters
- prefer arrays/spans/dense memory where access patterns support it
- no shared ownership unless true shared lifetime
- no silent fallback; fallbacks require warning log, metric, bound, test,
  and clear semantics

Before coding:
1. inspect relevant files/tests
2. state invariants
3. state ownership model
4. state failure modes
5. propose the minimal plan

Then implement, test, self-review, simplify, and report what was verified
and what was not.
```

## Review complex code

```text
Use the principal-production-engineer skill.

Review this code for production readiness against: simplicity, data-oriented
design, dense memory, explicit ownership/lifetime, memory safety, minimal
abstraction, explicit error handling, fail-fast vs designed degradation,
no silent fallback, hot-path performance, tests/benchmarks/fuzzing.

Output: verdict; blocker/major/minor findings; invariant gaps;
ownership/lifetime; failure semantics; data-layout/performance; unnecessary
complexity; minimal staged redesign; patch sketch; verification required
before merge.
```

## Redesign toward the doctrine

```text
Use the principal-production-engineer skill.

Redesign this code for: simple control flow, data-oriented layout, dense
memory, explicit ownership, clear failure semantics, no hidden
allocation/throwing/blocking, bounded observable fallbacks only,
tests and benchmarks.

Do not perform a broad rewrite unless necessary. Produce: current design
diagnosis; root causes; smallest staged redesign; API changes;
migration plan; required tests/benchmarks; representative patch sketch.
```

## Simplify generated code

```text
Now simplify your previous solution.

Delete every abstraction not required by current requirements.
Replace inheritance with composition/functions where possible.
Replace shared ownership with unique ownership plus borrows where possible.
Remove speculative config knobs.
Make failure and ownership explicit at API boundaries.
Keep only code that directly supports the tests and stated requirements.
```

## Red-team an implementation

```text
Red-team this implementation. Find:
- hidden allocation, throwing, blocking, or I/O
- unchecked return values
- ambiguous ownership or dangling-lifetime risks
- invalid states that remain representable
- silent fallbacks; unbounded retries/queues
- hot-path pointer chasing
- missing tests; benchmarks that would falsify any performance claim

Then propose the smallest fixes.
```

## Real-time control review

```text
Review this as a real-time control component. Check:
- deterministic execution; no dynamic allocation in the control loop
- no locks or bounded locking only; no exceptions
- no NaNs or invalid commands reaching actuators
- watchdog/deadline behavior; fail-safe state transitions
- compact fault reporting; observability outside the hard RT path
```

## Training pipeline review

```text
Review this as a training/data pipeline. Check:
- schema validation; dataset integrity
- corrupt-sample budget; retry/backoff limits
- NaN loss / gradient handling
- checkpointing; reproducibility
- logging/metrics for skipped data
- semantic-corruption fail-fast; infrastructure-failure robustness
```
