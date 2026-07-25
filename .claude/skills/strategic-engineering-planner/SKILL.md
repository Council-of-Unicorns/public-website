---
name: strategic-engineering-planner
description: Use before implementation when work is architecturally significant, ambiguous, multi-file, distributed, performance-sensitive, concurrency-heavy, safety-critical, or likely to need multiple passes. Forces exploration, requirement audit, architecture comparison, risk-driven planning, vertical slicing, and a written roadmap before any code is written. Skip for trivial fixes and obvious CRUD. Companion to `principal-production-engineer`, which takes over once the plan is approved.
---

# Strategic Engineering Planner

Plan first. Code last.

For complex tasks, planning quality dominates coding speed. This skill produces the roadmap; the `principal-production-engineer` skill executes against it.

## Use this skill when

The task is any of: architecturally significant, ambiguous, multi-stage, multi-file, distributed, performance- or latency-sensitive, infrastructure-heavy, concurrency-heavy, safety-critical, or likely to require multiple implementation passes.

Examples: protocols, distributed systems, databases, robotics stacks, training/inference infrastructure, media pipelines, networking systems, compilers, orchestrators, large refactors, platform redesigns.

Skip for: isolated bug fixes, mechanical edits, straightforward CRUD, tasks where the implementation is already obvious.

## Default behavior

Unless explicitly told otherwise:

1. Produce the roadmap.
2. Stop after the roadmap.
3. Wait for review before implementing.

## Core operating order

Apply strictly:

1. **Question requirements** — challenge what is asked.
2. **Delete scope** — remove what is not required.
3. **Simplify** — reduce what remains.
4. **Accelerate iteration** — invest in feedback loops.
5. **Automate last** — only stable, repeated, understood workflows.

Do not optimize before simplifying. Do not generalize before proving need. Do not automate before understanding.

## The planning loop

```text
Explore → Clarify goals → Audit requirements → Delete scope
       → Decompose → Compare architectures → Surface risks
       → State invariants → Design a vertical slice → Define milestones
       → Define verification → Then implement incrementally
```

### 1. Explore
Read the relevant files, interfaces, tests, configs, data flow, and operational constraints. Summarize what exists, what is missing, what is risky, what is unclear. Do not edit yet.

### 2. Clarify goals
Turn vague ambitions into measurable targets. Identify success metrics, hard constraints, soft constraints, non-goals, and unknowns.

| Vague | Measurable |
|---|---|
| "highly scalable" | "10k concurrent subscribers, p95 < 50ms" |
| "real-time" | "1 kHz deterministic loop, jitter < 100 µs" |
| "production-grade" | "bounded memory under slow consumers, graceful drain on shutdown" |

### 3. Audit requirements
For each major requirement: Who needs it? Why? What breaks if it is removed? Can it be deferred? Is it needed for v0? Reject requirements without measurable value, clear ownership, or concrete failure modes.

### 4. Delete scope
Defer or remove premature scaling, speculative extensibility, optional modes, excessive configuration, generalized frameworks, premature automation, unnecessary abstraction. A small correct system beats a large unfinished one.

### 5. Decompose the system
Identify: core entities, modules, interfaces, data flow, control flow, state machines, dependencies, ownership boundaries, resource lifecycles. Also: performance, concurrency, latency, memory, fault tolerance, deployment, observability, security, testing, recovery.

### 6. Compare architectures
For each major component, compare two or three approaches. Evaluate complexity, performance, scalability, maintainability, debuggability, operational burden, implementation speed, failure modes, risk. Do not converge on the first idea.

### 7. Plan by risk, not by feature
Ask: What is most likely to fail? Which assumption is dangerous? Which bottleneck dominates? What would invalidate the roadmap? For each top risk, write: cheapest experiment → success criterion → fallback. Attack highest-uncertainty items first.

### 8. State invariants
Write down system truths that must hold. Each important invariant should later map to a test, assertion, metric, or alert. Examples: memory is bounded; retries are bounded; queues have limits; failures are observable; state transitions are explicit; one slow consumer cannot block unrelated work; ownership is unambiguous.

### 9. Design a vertical slice
Prefer a thin end-to-end path over building layers in isolation. The first slice should prove core architecture viability, validate the hardest assumption, and exercise the hardest constraint. Examples: one relay path, one training run, one inference request, one control loop.

### 10. Define milestones
Each milestone has: goal, deliverable, scope, non-goals, dependencies, risks addressed, verification strategy, definition of done. Milestones should reduce uncertainty and unlock the next milestone.

### 11. Define verification
Before coding, decide how success is measured: unit, integration, simulation, property, fuzz, benchmark, load, latency histogram, chaos, profiling, deterministic replay, assertions. If verification is unclear, the architecture is unclear.

### 12. Implement incrementally
Once the plan is approved, hand off to the `principal-production-engineer` skill. Small diffs, tests alongside code, verify before expanding scope.

## Required planning output

When planning a complex task, produce all of:

```md
## Goal
## Success Metrics
## Constraints
## Non-Goals
## Requirement Audit
## Existing System Understanding
## Architecture Decomposition
## Core Entities and Interfaces
## Data Flow / Control Flow
## State Machines / Lifecycles
## Architecture Options
## Tradeoff Analysis
## Risks and Bottlenecks
## Invariants
## Vertical Slice Strategy
## Milestone Roadmap
## Verification Strategy
## Deferred Complexity
## Recommended Next Step
## Open Questions / Decision Points
```

Keep each section short and concrete. Empty or hand-wavy sections mean the plan is not ready.

## Behavioral rules

- Do not start coding for complex tasks.
- Do not assume requirements are correct.
- Do not overengineer v0.
- Do not optimize before measurement.
- Do not automate before understanding.
- Do not introduce abstractions without demonstrated need.
- Do not allow unbounded resource growth.
- Do not continue if architectural uncertainty remains high — stop and explore further.

## Core heuristic

> What is the smallest artifact or experiment that reduces the largest amount of uncertainty?

Build that first.
