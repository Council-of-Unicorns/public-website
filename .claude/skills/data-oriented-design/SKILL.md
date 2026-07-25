---
name: data-oriented-design
description: Doctrine and practice for writing extremely performant, machine-optimized code in any language. Use when performance is first-class — hot paths, real-time/embedded, low-latency, SIMD/vectorization, parsers, allocators, codecs, game/engine, HPC, or "as fast as possible." Covers model-the-computation; cache-line/SoA/hot-cold layout; indices over pointers; branchless control flow; SIMD (compare/movemask/ctz, blend, reduce); bit-packing/SWAR; radix sort; open-addressed hashing; arenas; and a measure-first protocol (perf, objdump, microbench). Routes to cpp-systems-internals for C++ mechanics.
license: MIT
metadata:
  author: eng-skills
  version: "1.0.0"
---

# Data-Oriented Design

How to write code that is fast *because it respects the machine* — the cache
hierarchy, the pipeline, the issue ports, the TLB — not because it looks clean.
This is the **mechanical-sympathy** layer: when the algorithm is already chosen
and you are fighting cycles.

> **One line:** *Understand the data and the hardware, then write the simplest
> direct code that transforms that data the way the machine wants — and prove the
> win with a profiler.*

## When to use

Load this skill when **performance is a stated, first-class requirement**, not a
nice-to-have:

- Hot paths: inner loops, per-frame / per-tick / per-packet / per-request work.
- Real-time / embedded / safety-critical control loops (bounded, no surprises).
- Low-latency systems (HFT, networking, codecs, databases, allocators, parsers).
- SIMD / vectorization, game engines, simulation, HPC, ML kernels.
- Any request to make code "as fast as possible," "branchless," "cache-friendly,"
  "SIMD," "zero-allocation," or to optimize a measured hot spot.

**When NOT to use:** cold code, I/O-bound or network-bound paths where compute is
noise, glue code, and anything where the data set is tiny and the call is rare.
DOD trades programmer convenience for machine efficiency; spend that trade only
where it pays. For correctness-first production discipline in general, that is
`principal-production-engineer`; to optimize one measured number unattended, that
is `auto-research`.

## The worldview (read `reference/doctrine_and_laws.md` for the full doctrine)

1. **The purpose of the program is to transform data.** Design starts from *what
   data exists, how much, and how it flows* — not from nouns/objects. *"Model the
   computation, not the world."*
2. **Hardware is the platform.** Memory latency dominates; the cache line, not the
   instruction, is the unit of work. Code exists to feed the machine data.
3. **Different data, different problem.** There is no context-free "right"
   structure — the access pattern decides the layout.
4. **The simple, direct transform is usually the fast one.** Abstraction that
   hides the data flow, the allocation, or the dispatch is the enemy of speed.

This is a real, named tradition (Acton's Data-Oriented Design; Thompson's
mechanical sympathy; the handmade / low-latency / game-engine schools; Warren's
*Hacker's Delight*; Drepper's memory paper). It is deliberately
counter-cultural to abstraction-first OOP. See the doctrine file.

## The optimization order — never skip a rung

Optimize in this order; a lower rung cannot fix a problem created higher up.

1. **Right algorithm / complexity** (and the right data structure for the access
   pattern). No micro-optimization rescues an O(n²) where O(n) exists.
2. **Data layout** — density, SoA vs AoS, hot/cold split, alignment. *This is the
   biggest lever after complexity and the one most often missed.*
3. **Ownership & lifetime** — arenas/pools for phase-based data; eliminate
   per-element allocation.
4. **Memory traffic** — fewer/larger sequential accesses; kill pointer chasing.
5. **Branch behavior** — make branches predictable or remove them.
6. **Vectorization / batching** — SIMD, batch APIs, amortized dispatch.
7. **Instruction-level / codegen** — inlining, L1i footprint, intrinsics, ILP.

Stop as soon as the measured target is met. **Each rung must be justified by a
measurement** (see the verification protocol).

## Hard rules (prefer / avoid)

| Prefer | Avoid | Why |
|---|---|---|
| Contiguous arrays, indices/handles | Pointer graphs, linked nodes, per-element `new` | Cache locality; the prefetcher works for you |
| SoA when a hot loop touches a subset of fields | AoS that drags cold fields through cache | Bandwidth + vectorization |
| Fixed capacity, no resize/relocate | Containers that reallocate under you | Stable addresses, no hidden alloc |
| Branchless select / blend on unpredictable conditions | `if` on data-dependent, ~50/50 branches | A mispredict is 10–20+ cycles |
| Batch / amortized work | One-item-at-a-time APIs in hot loops | Amortize call, lock, syscall, setup cost |
| Arena / pool with explicit phase lifetime | Scattered alloc/free of many small objects | One bulk reset; no fragmentation |
| Plain `struct` + free functions | Deep inheritance, virtual dispatch in hot loops | No vptr, full inlining/vectorization |
| `alignas(cache line)` on contended/SIMD data | Hot write-shared fields sharing a line | Kills false sharing (10×+ on contention) |
| Measure, then optimize | "This should be faster" | *Performance claims without measurement are folklore* |

Two non-negotiables: **no hidden allocation, blocking, throwing, or dynamic
dispatch in a declared hot path**, and **every "faster" claim carries a
benchmark**.

## Operating procedure

For a performance task, run this loop (it composes with
`principal-production-engineer`'s loop):

1. **Characterize the data.** Sizes, element layout, which fields are touched
   together, hot vs cold, lifetimes, cardinality, the dominant access pattern.
   *If you can't describe the data flow, you can't optimize it.*
2. **Find the actual bottleneck — measure first.** Profile before touching
   anything. Identify whether you are bound on memory, branches, compute, or
   front-end (L1i). Optimizing a non-bottleneck is wasted complexity.
3. **Establish a baseline and a target.** A committed scalar/obvious
   implementation and its number. The target is a number, not a vibe.
4. **Apply the lowest unsatisfied rung** of the optimization order; make the
   smallest change that addresses the measured bottleneck.
5. **Re-measure against the baseline.** Keep only if it beats the noise budget
   *and* still passes a correctness gate. Tie goes to the simpler code.
6. **Stop at the target.** Record what changed, the before/after numbers, and the
   command that proves it. Leave the baseline path documented if the fast path is
   conditionally compiled (ISA dispatch).

## Reference index — progressive disclosure

Load only the file relevant to the task.

### Foundations
- **[reference/doctrine_and_laws.md](reference/doctrine_and_laws.md)** — the
  worldview, the "three lies," the laws, when DOD applies and when it doesn't, and
  the canonical literature (Acton, Fabian, Thompson/Disruptor, Muratori,
  Warren, Drepper, Agner Fog).

### Design
- **[reference/data_layout.md](reference/data_layout.md)** — the layout decision
  discipline: SoA vs AoS, hot/cold split, density, indices and generational
  handles over pointers, arenas/pools, alignment and false sharing. Cross-language;
  routes to `cpp-systems-internals` for the C++ mechanics.
- **[reference/algorithms_and_structures.md](reference/algorithms_and_structures.md)**
  — choosing the structure/algorithm for the access pattern: open-addressed
  SIMD-scannable hash tables, fixed-capacity tables, radix/counting sort, when each
  beats the "default."

### Execution
- **[reference/control_flow_and_branchless.md](reference/control_flow_and_branchless.md)**
  — predication, `cmov`/select/blend, jump tables, sort-before-branch, the
  vectorization preconditions, branch hints.
- **[reference/simd_and_vectorization.md](reference/simd_and_vectorization.md)** —
  the SIMD idiom catalog: broadcast→compare→`movemask`→`ctz`, deferred
  OR-then-test reduction, lane-bit packing into an integer, running argmax via
  max+cmpeq+blend, horizontal-reduction ladders, `pshufb` as a parallel LUT, with
  worked kernel case studies.
- **[reference/bit_packing_and_swar.md](reference/bit_packing_and_swar.md)** —
  the bit toolbox (`x&-x`, `x&(x-1)`, `clz^31`, range masks), packing many fields
  into one word (atomic-state case study), IEEE-754 as a packed format, multi-word
  bit arrays and funnel shifts, multiply-as-scatter.

### Proof
- **[reference/measurement_and_verification.md](reference/measurement_and_verification.md)**
  — the measure-first protocol, the tools (`perf stat` counters, `perf c2c`,
  `objdump`/godbolt, `ncu`/`nsys`, `valgrind --tool=massif`), microbenchmark
  hygiene (`DoNotOptimize`, warmup, noise budget), and the code-review checklist.

## How to apply this material

When you write or review a performance-sensitive change:

1. **State the data and the bottleneck** — what data flows, and what the machine is
   actually bound on (from a profile, not a guess).
2. **Name the rung** of the optimization order you are on, and why the rungs above
   it are already satisfied.
3. **Show the mechanism** — what the cache/pipeline/ports do differently after the
   change (route to `cpp-systems-internals` for the C++/CPU mechanism depth).
4. **Show the measurement** — the exact tool, flags, and before/after number that
   prove the win, and the correctness gate that proves it is still correct.
5. **Keep it as simple as the speed allows** — delete the fast path if it isn't
   measurably faster on the real workload. Cleverness without a number is a
   liability.

## Companion skills

- `cpp-systems-internals` — the C++/CPU **mechanism** reference (cache lines,
  vtables, templates, linkage, `mmap`). This skill says *what to do*; that one says
  *what the machine does*. Load it for any C++-specific depth.
- `principal-production-engineer` — overall production discipline and the
  correctness/ownership/failure doctrine this performance work lives inside.
- `auto-research` — when the goal is to drive one measured number down/up
  unattended over many iterations on a fixed harness.
