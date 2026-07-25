# Design Doctrine

## North star

Make the program obvious to humans, obvious to the compiler, obvious to the CPU, and hard to misuse.

The best code has the fewest surprises:

- data flow is obvious;
- ownership is obvious;
- failure modes are obvious;
- performance model is obvious;
- tests encode promises;
- the next correct change is easy.

## The prime directive: minimize complexity

The enemy is state-space explosion:

- too many control paths;
- too many hidden allocations;
- too many implicit ownership relationships;
- too many dynamic dispatch paths;
- too many silent fallbacks;
- too many error paths hidden behind exceptions/callbacks/futures/frameworks;
- too many configs and modes.

An abstraction is good only when it reduces total complexity. It must provide semantic compression, enforce invariants, or localize real change.

## Distilled influences

### Carmack-style directness

Optimize for local reasoning. Hidden state, spooky action at a distance, and over-abstracted architecture are often worse than duplicated simple code.

Guidance:

- prefer direct code over clever code;
- prefer visible state over framework magic;
- prefer pure helper functions where practical;
- inline conceptually simple code if abstraction hides too much;
- measure instead of arguing aesthetics;
- keep the hot path inspectable.

### Stroustrup-style zero-overhead abstraction

Abstractions are good when they encode invariants and compile down to efficient code. They are bad when they add runtime, cognitive, ownership, and debugging cost without semantic compression.

Every abstraction must answer:

- what invariant does it enforce?
- what complexity does it hide?
- what dependency does it remove?
- what cost does it impose?
- can it be deleted later?

### Guido/Python-style readability

Explicit is better than implicit. Simple is better than complex. Flat is better than nested. Readability counts.

Guidance:

- avoid boolean parameter soup;
- prefer named options or specific functions;
- keep control flow flat;
- avoid clever metaprogramming unless it greatly simplifies usage;
- generate code that a tired reviewer can understand quickly.

### Knuth-style optimization discipline

Do not optimize blindly. But once the critical path is known, performance is engineering, not optional polish.

Optimization order:

1. correct algorithm;
2. data layout;
3. ownership/lifetime model;
4. concurrency model;
5. allocations/copies;
6. cache locality;
7. branch behavior;
8. vectorization/batching;
9. compiler hints;
10. instruction-level tuning.

### Karpathy-style feedback loops

The system is code + data + tests + evals + feedback loops. Agent-generated code must be constrained by invariants, tests, benchmarks, and human taste.

Use agents to accelerate iteration, not abdicate correctness.

## Anti-complexity laws

1. Every abstraction is guilty until proven useful.
2. Every hidden effect is technical debt.
3. Every pointer is a question.
4. Every boolean parameter is a small API failure.
5. Every dynamic dispatch in a hot path must defend itself.
6. Every fallback must be visible, bounded, tested, and measured.
7. Every benchmark claim needs a benchmark.
8. Every ownership transfer must be visible in the API.
9. Every new config knob creates a new state space.
10. Every broad rewrite must justify its blast radius.
11. Every global mutable object is a future debugging session.
12. Every catch-all handler must prove it cannot hide corruption.

## Simplicity hierarchy

Prefer, by default:

- function before class;
- plain struct before class hierarchy;
- composition before inheritance;
- direct call before callback;
- value/reference/span before pointer/smart pointer;
- `unique_ptr` before `shared_ptr`;
- vector/array/span before map/list/tree;
- IDs/indices before pointer graphs;
- static structure before runtime dynamism;
- explicit errors before exceptions;
- invariant-encoding types before comments;
- narrow interfaces before generic frameworks;
- deletion before extension.

## Abstraction acceptance test

An abstraction is acceptable when at least one is true:

- it enforces a real invariant;
- it hides difficult implementation behind a small stable interface;
- it localizes likely future change;
- it removes substantial duplication after the pattern is proven;
- it enables testing without service locators/global state;
- it does not obscure ownership, allocation, blocking, throwing, or performance.

Reject abstractions that mainly provide ceremony, speculative future-proofing, vocabulary inflation, or agent-generated fanciness.

## Control-flow doctrine

Use boring control flow:

- guard clauses;
- shallow nesting;
- explicit state machines for real state transitions;
- no hidden control flow through exceptions/callbacks/macros unless accepted by codebase conventions;
- no silent catch-and-continue.

## Production doctrine summary

The best code is not the code with the most patterns. It is the code where:

- the data flow is obvious;
- ownership is obvious;
- failure modes are obvious;
- performance model is obvious;
- tests encode promises;
- the next correct change is easy.
