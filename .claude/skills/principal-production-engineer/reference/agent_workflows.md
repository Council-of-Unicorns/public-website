# Agent Workflows for Complex Code

## Principle

Agents are fast junior engineers with broad knowledge and imperfect judgment. Use them for acceleration, not abdication.

Claude should work in tight loops:

```text
Explore -> Plan -> Implement -> Verify -> Review -> Simplify
```

## Complex implementation workflow

1. Read relevant code and tests before proposing changes.
2. Summarize current architecture in 5-10 bullets.
3. State invariants, failure modes, and ownership model.
4. Identify hot paths, external effects, and concurrency boundaries.
5. Propose the smallest viable design.
6. Ask clarifying questions only when blocked; otherwise make reasonable assumptions and label them.
7. Implement in small patches.
8. Add or update tests close to changed behavior.
9. Run available verification commands.
10. Self-review against this doctrine.
11. Simplify before final response.
12. Report exact verification status.

## Complex review workflow

1. Map modules and data flow.
2. Identify invariants and whether they are enforced.
3. Identify hidden ownership, allocation, I/O, throwing, blocking, and threading.
4. Identify over-abstraction and under-abstraction.
5. Identify unsafe fallbacks and error swallowing.
6. Identify data-layout problems and hot-path risks.
7. Identify missing tests, benchmarks, fuzzing, and runtime checks.
8. Propose staged redesign by risk-reduction per unit diff.
9. Provide a minimal patch sketch.
10. Define merge gates.

## Context management

- Keep a repo-level `CLAUDE.md` with non-negotiable rules.
- Keep task prompts specific.
- Avoid dumping massive doctrine into every prompt; reference this skill and load deeper files only as needed.
- Do not edit files outside the requested scope unless the dependency is necessary and explained.
- Prefer small, reviewable diffs.
- Preserve existing style unless style is the problem.

## Anti-agent failure modes

Watch for:

- hallucinated APIs;
- invented requirements;
- overbroad rewrites;
- shallow tests that only prove the happy path;
- “performance improvements” without measurement;
- unnecessary abstractions;
- hidden dependencies;
- unchecked error paths;
- claiming tests passed when not run;
- silently changing public behavior.

## Good agent instructions

Use constraints like:

- no dynamic allocation after construction;
- no exceptions;
- use `[[nodiscard]] bool noexcept` for simple expected failure;
- no virtual dispatch in hot path;
- no `shared_ptr` unless true shared lifetime;
- prefer arrays/spans/SoA where access pattern supports it;
- add tests for empty/full/wraparound/error paths;
- add benchmark for hot path;
- preserve existing API unless migration plan included;
- minimize blast radius;
- remove abstractions that are not necessary.

## Red-team prompts

Ask Claude to critique its own code:

- What hidden allocation remains?
- What can throw?
- What can block?
- What ownership is ambiguous?
- What invariant is only documented, not enforced?
- What fallback can silently corrupt results?
- What path lacks tests?
- What abstraction can be deleted?
- What benchmark would disprove the performance claim?

## Final reporting format

Claude should report:

- changed files;
- behavioral changes;
- invariants enforced;
- tests/benchmarks run;
- tests/benchmarks not run and why;
- remaining risks;
- suggested next step.
