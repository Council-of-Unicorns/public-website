# /redesign-principal

Invoke the `principal-production-engineer` skill to redesign code toward the doctrine. Prefer the smallest redesign that fixes root causes; avoid grand rewrites unless current design prevents correctness, safety, or performance.

Required output:

1. **Current architecture** — concise summary.
2. **Root causes** — not symptoms.
3. **Target design** — minimal end-state.
4. **Data layout / ownership** — dense memory, IDs vs pointers, who owns what.
5. **Failure / degradation policy** — fail-fast vs bounded observable degradation.
6. **API changes** — what breaks, why, and how callers migrate.
7. **Staged patch plan** — ordered by risk reduction per unit diff.
8. **Tests / benchmarks / rollout gates** — what must pass at each stage.

For architecturally significant redesigns, run the `strategic-engineering-planner` skill first to produce the roadmap.
