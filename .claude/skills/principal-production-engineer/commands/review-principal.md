# /review-principal

Invoke the `principal-production-engineer` skill to review the selected code or repository area at principal-engineer standard.

Required output:

1. **Verdict** — production-ready / ship with fixes / risky but salvageable / not production-ready / unsafe for requirements.
2. **Top risks** — 3–7 highest-leverage risks.
3. **Blockers** — must fix before merge.
4. **Majors** — should fix before merge unless explicitly accepted.
5. **Minors** — improve if touching nearby code.
6. **Invariant gaps** — what must hold but is not enforced.
7. **Ownership / lifetime** — pointers, references, spans, callbacks, arenas, shared state.
8. **Failure semantics** — fail-fast vs degradation, silent fallbacks, ignored results, retry budgets.
9. **Data layout / performance** — density, hot/cold split, pointer chasing, allocations, locking, batching.
10. **Complexity** — abstractions earning their keep; deletable modules.
11. **Test / benchmark gaps.**
12. **Minimal staged redesign** — ordered by risk reduction per unit diff.
13. **Patch sketch** — representative code where it helps.
14. **Merge gate** — exact verification required before merge.

Do not list style nits. Be direct.
