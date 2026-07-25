# Review Gate

Use before approving a change.

## Blocker checks

- [ ] No memory safety issues.
- [ ] No data races or ambiguous shared mutable state.
- [ ] No ignored critical return values.
- [ ] No silent fallback that can corrupt state/results.
- [ ] No fail-open security/integrity behavior.
- [ ] No unbounded queue/retry/cache in production path.
- [ ] No hidden allocation/blocking/throwing in hard real-time path.
- [ ] No semantic corruption in training/data path.

## Design checks

- [ ] Data flow is obvious.
- [ ] Ownership is obvious.
- [ ] Failure modes are obvious.
- [ ] Performance model is obvious for hot paths.
- [ ] Abstractions enforce invariants or remove real complexity.
- [ ] Public API is hard to misuse.
- [ ] Invalid states are minimized or impossible.
- [ ] Dependencies are visible and narrow.

## Verification checks

- [ ] Tests cover normal, edge, and error paths.
- [ ] Fuzz/property tests exist where appropriate.
- [ ] Benchmarks support performance-sensitive claims.
- [ ] CI/static/sanitizer checks are adequate.
- [ ] Rollback/deployment risk is understood.

## Review output

- [ ] Verdict stated.
- [ ] Findings prioritized by severity.
- [ ] Required fixes before merge listed.
- [ ] Optional improvements separated from blockers.
- [ ] Minimal redesign path provided when needed.
