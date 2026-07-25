# Principal-Level Code Review Rubric

Use this rubric for serious production code review and redesign.

## Verdict levels

- **Production-ready**: correct, simple, tested, observable, and aligned with the codebase.
- **Ship with fixes**: mostly sound; requires bounded changes before merge.
- **Risky but salvageable**: root design is acceptable, but important safety/performance/test gaps exist.
- **Not production-ready**: significant correctness, ownership, failure, complexity, or verification issues.
- **Unsafe for requirements**: can violate safety, security, data integrity, real-time constraints, or semantic correctness.

## Finding severity

### Blocker

Must fix before merge. Examples:

- data corruption;
- memory safety bug;
- race condition in shared mutable state;
- silent fallback that can corrupt results;
- ignored error in critical path;
- unbounded retry/queue in production path;
- security/auth fail-open;
- hard real-time path can allocate/block/throw unexpectedly.

### Major

Should fix before merge unless explicitly accepted. Examples:

- ambiguous ownership;
- insufficient tests for critical behavior;
- hidden allocation in likely hot path;
- overbroad rewrite;
- poor failure classification;
- hard-to-debug abstraction layer;
- performance claim without benchmark.

### Minor

Improve if touching nearby code. Examples:

- naming clarity;
- local simplification;
- minor API ergonomics;
- missing comment for non-obvious invariant.

### Nit

Optional style issue with little production risk.

## Review categories

### Invariants

- What must always be true?
- Are invalid states representable?
- Are invariants encoded in types or only comments?
- What happens when invariant checks fail?
- Are debug/release behaviors appropriate?

### Ownership/lifetime

- Who owns each object?
- Can pointers be null?
- Can references/spans dangle?
- Is `shared_ptr` justified?
- Are callbacks storing references across lifetimes?
- Are arena objects escaping?
- Is shared mutable state synchronized and owned by a clear component?

### Failure semantics

- Are failures explicit at call sites?
- Are return values checked?
- Are `[[nodiscard]]` annotations used where needed?
- Can code throw unexpectedly?
- Are exceptions smuggled through callbacks/futures/task systems?
- Are fallbacks visible, bounded, tested, and measured?
- Are fatal conditions distinguished from expected environmental failures?

### Data and performance

- Is data stored densely?
- Are hot and cold fields separated?
- Is there pointer chasing in hot loops?
- Are operations batched?
- Are allocations hidden in hot paths?
- Are maps/trees/lists justified by access pattern?
- Are lock/contention risks clear?
- Are branch-heavy paths measured?
- Is SIMD/vectorization possible or blocked by layout?

### Complexity

- Are abstractions earning their keep?
- Is inheritance used for substitutability or code reuse?
- Is dependency injection revealing dependencies or creating ceremony?
- Are there speculative config knobs?
- Can modules be deleted cleanly?
- Is global state avoided?
- Is the simple path still visible?

### Testing and verification

- Unit tests for normal/edge/error paths?
- Property tests for invariants?
- Fuzz tests for parsers/protocols?
- Integration tests for boundaries?
- Benchmarks for hot paths?
- Load/soak tests for production behavior?
- Sanitizers/static analysis for memory/thread issues?
- Regression tests for known bugs?

## Output structure

1. Verdict.
2. Top risks.
3. Blockers.
4. Major findings.
5. Minor findings.
6. Minimal staged redesign.
7. Representative patch sketch.
8. Required verification before merge.
9. Residual risks after fixes.
