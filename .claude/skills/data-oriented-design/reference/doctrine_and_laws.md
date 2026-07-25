# Doctrine & laws

The worldview behind every other file in this skill. Load this to understand
*why* the patterns are what they are, when the philosophy applies, and where it
sits in the literature.

## The core claim

**A program's job is to transform input data into output data. Everything else —
types, objects, abstractions — exists only to serve that transform.** Design
therefore starts from the data: how much there is, how it is laid out, which parts
are touched together, and how it flows through the machine. *Model the
computation, not the world.*

The bottleneck on modern hardware is almost never arithmetic; it is **getting the
right bytes into the core**. A main-memory miss is hundreds of cycles; an
L1 hit is a few. The unit of work is the **cache line (64 bytes)**, not the
instruction. Code that ignores this loses 10–100× to code that doesn't, regardless
of how elegant it is.

## The three lies (Acton) — what DOD rejects

1. **"Software is the platform."** No — the *hardware* is the platform. Memory
   latency, cache size, branch predictors, and SIMD width are the real constraints;
   the language is a tool for emitting instructions that respect them.
2. **"Code should be designed around a model of the world."** No — code should be
   designed around the data and its transformations. Real-world taxonomies
   (inheritance trees, "is-a" hierarchies) rarely match how the data is actually
   processed.
3. **"Code is more important than data."** No — the data layout and volume
   determine the performance and even the structure of the code. *If you don't
   understand the data, you don't understand the problem.*

## The laws

1. **The access pattern dictates the layout.** There is no context-free "best"
   structure. Fields read together belong together; fields scanned independently
   belong apart (SoA). Decide layout from the hot loop, not from the entity.
2. **Density first.** Prefer contiguous, index-addressable storage. Be suspicious
   of every pointer (it is a potential cache miss and a question about ownership),
   every linked node, and every per-element allocation.
3. **Hardware sympathy is engineering, not folklore.** Reason in cache lines,
   pages, branches, dependency chains, and issue ports — and prove it with counters.
4. **The simplest direct transform usually wins.** Abstractions that hide the data
   flow, allocation, dispatch, or blocking are the enemy of both speed and
   debuggability. Accept an abstraction only when it compiles down to the same code
   you'd write by hand *and* earns its keep (semantic compression, an enforced
   invariant). Otherwise inline it.
5. **Measure or it didn't happen.** A "faster" claim without a benchmark is
   folklore. Every optimization is a hypothesis the profiler confirms or kills.
6. **Optimize the bottleneck, nothing else.** Speeding up code that isn't the
   bottleneck adds complexity and risk for zero gain.

## When DOD applies — and when it doesn't

| Apply it | Don't bother |
|---|---|
| Hot loops, per-frame/tick/packet/request work | Cold setup/teardown, run-once code |
| Large N (arrays, batches, streams) | Tiny N, rare calls |
| Real-time / low-latency / embedded budgets | I/O-bound or network-bound paths (compute is noise) |
| SIMD/throughput-critical kernels | Glue, config parsing, CLI plumbing |
| Memory-bound traversal | Code dominated by an external service's latency |

DOD is a **trade**: programmer convenience and "natural" modeling for machine
efficiency. Spend the trade only where the machine time matters. Misapplied, it is
premature optimization that hurts readability for no measured gain. The discipline
is knowing where the line is — which is why measurement (not taste) decides.

## Relationship to other philosophies

- **Vs. OOP / domain modeling:** DOD inverts the default. Objects bundle data with
  behavior and scatter it across the heap; DOD separates data (dense arrays) from
  transforms (functions over those arrays). Inheritance is for substitutability,
  never code reuse.
- **Vs. Clean Code / SOLID:** DOD treats many "clean" abstractions (deep layering,
  dependency injection, one-class-per-concept) as locality-destroying overhead.
  *"Modularity that destroys locality is not good engineering."*
- **Vs. "premature optimization is the root of all evil":** DOD agrees you must
  measure first, but rejects the common misreading ("never think about
  performance"). Layout decisions are architectural — expensive to retrofit — so
  they are made up front *from the data*, then validated.
- **Zero-overhead abstraction:** the goal, not the assumption. DOD insists you
  verify that an abstraction actually compiled to zero overhead, because in
  practice many don't.

## The canonical literature (for citations, not folklore)

- **Mike Acton**, "Data-Oriented Design and C++" (CppCon 2014) — the foundational
  talk; the three lies; "model the computation."
- **Richard Fabian**, *Data-Oriented Design* (2018) — book-length treatment; ECS.
- **Noel Llopis**, "Data-Oriented Design (Or Why You Might Be Shooting Yourself in
  the Foot with OOP)" (2009).
- **Martin Thompson** et al., the **LMAX Disruptor** (2011) — "mechanical
  sympathy," cache-line padding, single-writer principle, lock-free ring buffer.
- **Casey Muratori** — *Handmade Hero*; "Clean Code, Horrible Performance";
  "compression-oriented programming" / **semantic compression**.
- **Henry S. Warren**, *Hacker's Delight* — the bit-manipulation bible.
- **Ulrich Drepper**, "What Every Programmer Should Know About Memory" (2007) — the
  cache/TLB/paging worldview.
- **Agner Fog**, optimization manuals + instruction tables — microarchitecture and
  latency/throughput data.
- **Carl Cook**, "When a Microsecond Is an Eternity" (CppCon 2017) — the
  low-latency (HFT) expression of the same discipline.

Where these communities live: game/engine dev (Insomniac, Naughty Dog, id),
low-latency/HFT, embedded/real-time/aerospace, HPC, kernels. Well known *there*;
counter-cultural to mainstream enterprise OOP.

## Applying the doctrine in practice

When you make or review a performance decision, you should be able to say, in
order: **(1)** what the data is and how it flows; **(2)** what the machine is bound
on (from a profile); **(3)** which layout/transform the data wants; **(4)** the
measurement that confirms it. If any of those four is missing, the optimization is
a guess. The other reference files in this skill are the toolbox for step (3); the
measurement file is step (2) and (4).
