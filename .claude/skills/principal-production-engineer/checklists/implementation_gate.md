# Implementation Gate

Use before considering a production implementation complete.

## Before coding

- [ ] Relevant code/tests inspected.
- [ ] Existing style and error-handling conventions understood.
- [ ] Invariants stated.
- [ ] Ownership/lifetime model stated.
- [ ] Expected vs unexpected failures classified.
- [ ] Fail-fast vs degradation policy decided.
- [ ] Hot paths identified.
- [ ] Verification plan defined.
- [ ] Public API/product behavior changes identified.

## During coding

- [ ] Diff remains narrow.
- [ ] Simple direct code preferred.
- [ ] No speculative abstraction added.
- [ ] Ownership visible in API/types.
- [ ] No hidden allocation in hot paths.
- [ ] No hidden exceptions in non-throwing APIs.
- [ ] No hidden blocking/I/O behind innocent names.
- [ ] `[[nodiscard]]` used for must-check results.
- [ ] `noexcept` used only where contract is true.
- [ ] Arenas/pools have explicit lifetime.
- [ ] Fallbacks are visible, bounded, tested, and measured.
- [ ] No unbounded retries/queues/caches without justification.

## After coding

- [ ] Unit/regression tests added or updated.
- [ ] Edge/error paths tested.
- [ ] Property tests added where invariants are broad.
- [ ] Fuzz tests added/updated for parsers/untrusted input.
- [ ] Benchmark added/updated for performance-sensitive code.
- [ ] Formatting/lint/type/static checks run where available.
- [ ] Sanitizers or thread checks considered for unsafe/concurrent code.
- [ ] Self-review performed.
- [ ] Unnecessary abstractions/options/dead code removed.
- [ ] Verification reported truthfully.
