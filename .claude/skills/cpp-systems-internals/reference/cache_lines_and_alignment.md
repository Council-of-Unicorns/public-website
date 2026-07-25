# Cache Lines, Alignment, and False Sharing

## Cache line geometry

The CPU never reads main memory one byte at a time. The memory subsystem operates on **cache lines** — fixed-size blocks, **64 bytes** on virtually all modern x86_64 and ARM cores.

Accessing address `X` pulls the entire 64-byte line containing `X` into L1d. Subsequent accesses to `X+1`, `X+2`, … hit the same line at L1 speed. This is **spatial locality**.

### Implications for data structures

- **Contiguous arrays** — `std::vector<int>`, `std::array`: iterating loads 16 ints per line. Streaming traversal yields near-100% L1d hit rate.
- **Linked structures** — `std::list`, pointer-chasing trees, `std::map`: each node is at a random address. Each hop is a fresh 64-byte fetch; the rest of the line is wasted. Cache hit rate collapses.

Rule of thumb: prefer dense, index-addressable storage in hot paths. Reserve pointer graphs for access patterns that don't benefit from contiguity.

## False sharing

A multi-threaded performance bug where two threads on different cores modify **distinct** variables that happen to share a cache line.

```cpp
struct CoLocatedData {
    int thread1_counter;   // bytes 0–3
    int thread2_counter;   // bytes 4–7  ← same 64-byte line
};
```

Under MESI (the cache coherence protocol):

1. Core 1 writes `thread1_counter` → its copy of the line transitions to **Modified**.
2. The protocol invalidates the line in Core 2's L1d.
3. Core 2 writes `thread2_counter` → must reload the line from Core 1 (or shared L3).
4. Core 1's next write re-invalidates Core 2's copy. Repeat indefinitely.

This **cache line bouncing** is invisible to the programmer but can collapse multi-threaded throughput by 10× or more — even though the algorithm has no logical contention.

## `alignas` and `alignof`

C++11 added `alignas` for explicit alignment control.

```cpp
struct alignas(64) HighPerformanceLine {
    int data[16];        // 16 × 4 = 64 bytes exactly
};
```

### Fixing false sharing

Place each contended variable on its own line:

```cpp
#include <new>

struct ThreadIsolatedCounters {
    alignas(std::hardware_destructive_interference_size) int worker1_accumulator;
    alignas(std::hardware_destructive_interference_size) int worker2_accumulator;
};
```

- `std::hardware_destructive_interference_size` (C++17) — the implementation's hint at cache-line-bouncing granularity (typically 64; sometimes larger on prefetch-pair architectures).
- `std::hardware_constructive_interference_size` — the granularity for grouping data that *should* share a line.

### Constraints

- `alignas(X)` accepts only powers of two; non-powers fail to compile.
- `alignas` can only **strengthen** alignment, not weaken it. `alignas(1) int x;` is silently ignored because `int` requires natural 4-byte alignment.
- `alignof(T)` returns the natural alignment of `T` (e.g., `alignof(double) == 8`).

## When to use

- Per-thread counters, queue heads/tails, statistics counters, hot atomic flags — all candidates for forced isolation.
- Conversely: aggressively packing rarely-accessed cold fields is fine; only hot, write-contended fields suffer from false sharing.
- Verify with `perf c2c` (Linux), which directly reports cache-line contention events with source-line attribution.

## Related techniques

- **Padding** — for fields that should share a line for spatial locality, group them; for fields that should not, pad to the line boundary.
- **Struct-of-Arrays (SoA)** — when iterating one field across many records, SoA loads only that field's lines instead of full records.
- **Cache-aware allocation** — `posix_memalign` / `std::aligned_alloc` / `operator new(std::align_val_t)` for guaranteed-aligned heap blocks.
