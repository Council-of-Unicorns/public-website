# /implement-principal

Invoke the `principal-production-engineer` skill to implement the requested change.

Required loop:

1. **Explore** — relevant files, tests, build config, error-handling style.
2. **Map** — data flow, ownership boundaries, failure paths, hot paths.
3. **State** — invariants, ownership model, failure model, performance model (hot paths only).
4. **Plan** — the smallest safe change and the exact files to touch.
5. **Implement** — narrow, local patches; preserve unrelated behavior.
6. **Test** — add/update unit, property, fuzz, or benchmark coverage proportional to risk.
7. **Verify** — run available checks; if a check cannot be run, say so and give the exact command.
8. **Self-review** — hidden allocation/throwing/blocking, ambiguous ownership, untested paths.
9. **Simplify** — delete speculative abstractions, dead code, unused options.
10. **Report** — changed files, why, verified, not verified, risks, next step.

Do not ask for confirmation when the next safe step is obvious.
