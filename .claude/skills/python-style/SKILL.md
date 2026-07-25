---
name: python-style
description: Python-specific style and design guidance. Use when writing or reviewing Python where control-flow complexity, abstraction choice, or idiom matters — flattening logical branches (guard clauses, dispatch over `if`/`elif` chains), enums/`StrEnum` over magic strings, fail-fast validation (narrow `except`, no silent fallbacks), no optional imports (`try`/`except ImportError`) and no redundancy, and choosing abstractions (ABC vs `Protocol`, composition over inheritance). Each topic is a separate reference file; load only what's relevant. Routed to from `principal-production-engineer`.
---

# Python Style

Python-specific style and design discipline for coding agents: keep control flow flat, make illegal states unrepresentable, fail loudly, and abstract only when a second real case forces it. Each topic below has its own reference file; load only the one relevant to the task.

## When to use

- Writing or reviewing Python where branch count, nesting, or duplicated conditionals are getting hard to follow.
- Deciding how to model a fixed set of choices (modes, states, kinds) or how to dispatch on it.
- Reviewing error handling, `try`/`except` scope, fallbacks, and defensive defaults.
- Introducing an interface or base class — or pushing back on one that isn't earned yet.
- Steering another coding agent toward idiomatic, low-branch, fail-fast Python.

Pair with `principal-production-engineer` for the language-agnostic doctrine ("what to prefer" and "how to verify"); this skill is the Python-specific translation of it. For C++ specifics load `cpp-systems-internals` instead.

## Reference index — progressive disclosure

Load only the files relevant to the current question.

### Control flow and dispatch

- **[reference/control_flow.md](reference/control_flow.md)** — reduce logical branches: guard clauses and early returns, flatten the arrow anti-pattern, replace `if`/`elif` ladders with dict dispatch or `match`, polymorphism over `isinstance` ladders, no boolean-parameter soup, complexity (`C901`) as the signal.
- **[reference/enums_over_strings.md](reference/enums_over_strings.md)** — replace magic strings used as discriminants with `Enum`/`StrEnum`/`IntEnum`/`Literal`; `match` + `assert_never` for exhaustiveness; dict dispatch keyed by enum; which enum class to pick.

### Failure and dependencies

- **[reference/fail_fast.md](reference/fail_fast.md)** — validate at the boundary then trust inward; raise at the cause; narrow `except`; no bare `except`/silent swallow; the failure taxonomy; why defensive defaults (`.get(k, d)`, `x or d`) hide bugs; `assert` vs `raise`.
- **[reference/imports_and_redundancy.md](reference/imports_and_redundancy.md)** — no optional imports (`try`/`except ImportError`); top-level unconditional imports; required deps declared, genuine optionals as extras that raise actionable errors; collapse duplicated logic/constants/validation to one home without over-DRYing.

### Abstraction design

- **[reference/abstractions_and_abc.md](reference/abstractions_and_abc.md)** — which mechanism (function vs `Protocol` vs ABC vs `@dataclass` vs `Enum`); `Protocol` (structural) vs ABC (nominal + shared code); composition over inheritance; when *not* to abstract; speculative-framework anti-patterns.

## How to apply this material

When a question touches a topic here:

1. State the concrete rule and *why* it reduces branches, failure surface, or coupling.
2. Show the prefer/avoid pair — the references give you idiomatic before/after code.
3. Tie the fix to enforcement: the relevant `ruff`/`mypy`/`pyright` selector that makes the rule a build failure, not a style opinion.
4. Don't over-correct — every file names where the rule *stops* applying (simple two-deep `if`, legitimate defaults, coincidental similarity, Protocol-where-a-Callable-suffices).

The throughline matches `principal-production-engineer`: **simple code, explicit state, visible failure, minimal abstraction** — expressed in Python idiom and made enforceable by the type checker and linter.
