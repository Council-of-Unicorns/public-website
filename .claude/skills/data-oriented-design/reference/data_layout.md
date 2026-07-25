# Data layout

The highest-leverage rung after algorithmic complexity. Load this when deciding
how to store data that a hot path touches. Language-agnostic; for the C++
mechanics (cache-line size, `alignas`, false sharing, generational handles, ECS,
allocators) load `cpp-systems-internals` and read `reference/data_oriented_design.md`
and `reference/cache_lines_and_alignment.md`.

## Doctrine

**Lay the data out the way the hot loop reads it.** Decide from the access
pattern, never from the entity taxonomy. The cache line (64 B) is the unit moved;
every byte you drag in and don't use is wasted bandwidth and evicted useful data.

## The layout decision procedure

1. **List the hot loops.** For each, write down exactly which fields it reads and
   writes per element.
2. **Group by co-access.** Fields touched together in the hot loop go together;
   fields touched in different loops go apart.
3. **Pick AoS or SoA per group** (table below).
4. **Split hot from cold.** Move rarely-touched fields out of the hot record into a
   side table indexed by the same handle.
5. **Choose addressing** — index/handle over pointer (next section).
6. **Choose lifetime** — arena/pool if phase-based (next section).
7. **Align** to the access unit; isolate write-contended words.

## AoS vs SoA

| Use AoS (`struct{...} arr[]`) | Use SoA (`field0[]; field1[]; …`) |
|---|---|
| The hot loop uses *most* fields of each element together | The hot loop touches *one or a few* fields across many elements |
| Random access to whole elements | Streaming/scan, especially vectorizable |
| Small structs that fit in a line anyway | Wide structs where one field is hot |

- **Default for streaming numeric work: SoA.** It streams only the needed arrays
  and vectorizes cleanly; AoS loads cold fields for every element and wastes
  bandwidth and SIMD lanes.
- **When unsure, implement both and benchmark** — the win depends on the real
  access ratio.

## Hot/cold split

- Keep the hot record tiny: only the fields the inner loop touches every
  iteration. Push diagnostics, names, config, rarely-read state into a **cold side
  table** keyed by the same index/handle.
- Effect: more elements per cache line (often 2–5×), so the hot loop touches fewer
  lines and the prefetcher keeps up.
- Pack flags into bits rather than one `bool` per byte when memory is the binding
  constraint (see `reference/bit_packing_and_swar.md`).

## Density: indices and handles over pointers

- **Replace pointer graphs with integer indices into arrays.** Indices are smaller
  (often 4 B vs 8), survive relocation/serialization, keep data dense, and remove a
  pointer-chase (a likely cache miss) per hop.
- **Generational `(slot, generation)` handles** detect use-after-free on reused
  slots: a stale handle whose generation no longer matches returns "not found"
  instead of aliasing a new occupant. This is the workhorse for object pools, ECS,
  and any system handing out stable references into a moving array.
- *Every pointer is a question* — about ownership, lifetime, and whether the next
  access misses cache. Prefer values, references/spans, and indices; reach for raw
  or smart pointers only when ownership genuinely requires them (see
  `principal-production-engineer/reference/memory_data_ownership.md`).

## Lifetime: arenas and pools

- **When lifetimes are phase-based** — per request / tick / frame / packet batch /
  simulation step / parse — allocate from an **arena** (bump allocator) and reset
  the whole thing at the phase boundary. One bulk free; no per-object `free`; no
  fragmentation; allocation is a pointer add.
- Pass the arena explicitly as a scratch parameter (`work(input, Arena& scratch)`),
  make its lifetime obvious, and forbid arena-allocated objects from escaping the
  phase.
- **Fixed-capacity, never-resize structures** give permanently stable addresses and
  zero hidden reallocation — a design property, not a wrapper. Decide the capacity
  and load factor up front.
- For the C++ vocabulary (`std::pmr`, monotonic buffer resource, escape-hazard
  testing), load `cpp-systems-internals` → `reference/cpp_ownership_and_arenas.md`.

## Alignment & false sharing

- **Align hot data to the access unit:** 64 B for whole-line / AVX2 loads, the SIMD
  width for vector loads (e.g. 32 B for AVX2, 64 B for AVX-512).
- **False sharing:** if two threads write different variables that land on the same
  cache line, the line bounces between cores (MESI) and throughput can collapse
  10×+ with *no logical contention*. Pad/align each independently-written field (or
  the whole per-thread struct) onto its own line.
- Cold, rarely-written fields can be packed freely — only hot write-shared fields
  suffer false sharing.

## Anti-patterns

- `vector<unique_ptr<Base>>` iterated polymorphically in a hot loop — heap
  fragmentation + a vptr load + missed inlining *per element*.
- `unordered_map<string, T>` on a hot path — hashing a string + chained-node
  pointer chasing + per-node allocation. Intern to an integer key and use an
  open-addressed table.
- A linked list "for O(1) insert" chosen without measuring — almost always loses to
  a vector + shift for realistic sizes because of locality.
- Deep object trees with bidirectional parent/child pointers walked every frame.
- One `bool`/`enum`/pointer per element when a parallel bit-set or small index
  would do.

## Code-review checklist

- [ ] Is the layout shaped like the dominant access pattern (SoA where a loop
      touches a field subset)?
- [ ] Are hot and cold fields separated?
- [ ] Are pointer graphs replaced by indices/handles where relocation or density
      matters?
- [ ] Is per-element allocation eliminated from hot paths (arena/pool/fixed cap)?
- [ ] Is ownership of arena/pool data visible and escape-free?
- [ ] Are write-contended fields isolated to their own cache line?
- [ ] Is the structure aligned to its access/SIMD unit?

## Verification commands

```bash
perf stat -e cache-misses,cache-references,L1-dcache-load-misses,LLC-load-misses ./bench
perf stat -e dTLB-load-misses,page-faults ./bench       # paging / TLB pressure
perf c2c record ./bench && perf c2c report               # false sharing (HITM lines)
valgrind --tool=massif ./bench                           # footprint / allocation peaks
heaptrack ./bench                                         # allocation count/sites
```
Look for: a high miss rate that drops after SoA/hot-cold; LLC misses dropping after
density changes; HITM events disappearing after `alignas`; allocation count → ~0 in
the hot path after arena adoption.
