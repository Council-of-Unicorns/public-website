# CPU Pipelines and the L1 Instruction Cache

## L1i geometry

Each modern CPU core has split L1 caches: an L1 data cache (L1d) and an L1 instruction cache (L1i). The L1i is small — typically **32 KB to 64 KB per core**.

The CPU cannot execute instructions directly from main RAM at full speed. Instructions must be fetched into L1i first:

- **Cache hit** — the working instruction set fits in L1i; instructions stream at full pipeline throughput.
- **Cache miss** — code exceeds L1i; the pipeline stalls while fetching from L2/L3 or RAM (tens of cycles minimum).

## How templates churn the L1i

A 10 KB function written once and called over base pointers occupies 10 KB of L1i regardless of how many types pass through it.

The same logic written as a template, instantiated for `int`, `float`, `double`, and `std::string`, emits **four** 10 KB copies — 40 KB total. If a hot loop alternates over these specializations:

```cpp
for (size_t i = 0; i < 10000; ++i) {
    process<int>(integer_data);          // load 10 KB into L1i
    process<float>(float_data);          // load 10 KB into L1i
    process<double>(double_data);        // load 10 KB into L1i  (30 KB now resident)
    process<std::string>(string_data);   // load 10 KB — L1i is 32 KB; evict <int>
}
```

Working set (40 KB) > L1i capacity (32 KB) → the cache thrashes, evicting and reloading specializations every iteration.

### Mitigation: Thin Template pattern

Strip type-independent logic out of the template; put it in a non-templated base. The base compiles **once** and stays resident; the template body shrinks to type-specific glue.

Before (cache-hostile):

```cpp
template <typename T>
class LargeVector {
    T* storage;
    int size;
    void print_error_log() { /* 2 KB of formatting */ }
    void balance_internal_nodes() { /* 5 KB of pointer ops */ }
};
// Each instantiation duplicates 7 KB of type-independent code.
```

After (Thin Template):

```cpp
class VectorBase {                                       // compiled exactly once
protected:
    int size;
    void print_error_log();
    void balance_internal_nodes();
};

template <typename T>
class ThinVector : public VectorBase {                   // minimal type-dependent shell
    T* storage;
};
```

libstdc++ and libc++ use variants of this technique inside `std::vector`, `std::map`, and friends.

## The instruction pipeline

CPUs are pipelined: a single instruction passes through stages, and a new instruction enters the front each cycle.

> Fetch → Decode → Execute → Memory Access → Write Back

Pipelining yields ~1 instruction per cycle in steady state — until something stalls it.

### Hazards

- **Data hazard** — an instruction depends on the result of a not-yet-completed predecessor; the pipeline freezes (or forwards, where possible).
- **Structural hazard** — two instructions need the same hardware unit at the same time.
- **Control hazard** — a branch's outcome is not known until Execute, but the front-end must keep fetching. The CPU **predicts** the branch direction.

### Branch misprediction

If the branch predictor is wrong, in-flight instructions on the wrong path must be discarded and the pipeline refilled from the correct address. The penalty is typically **10–20+ cycles** on modern x86.

Predictors are highly accurate on regular patterns (loops, monotonic conditionals) and poor on random data. Sorting data before a hot conditional can be faster than not sorting it — purely because of predictor accuracy.

### Compiler-assisted mitigations

- **Loop unrolling** — eliminates the loop-condition branch entirely for fixed iteration counts:

  ```cpp
  // before
  for (int i = 0; i < 4; ++i) array[i] = 0;

  // after (compiler-driven unroll)
  array[0] = 0; array[1] = 0; array[2] = 0; array[3] = 0;
  ```

- **`[[likely]]` / `[[unlikely]]`** (C++20) — hints to the predictor. Use sparingly and only when the bias is measured.
- **Branch-free code** — `std::min`/`std::max`, conditional moves, table lookups can avoid branches entirely in hot inner loops.

## Measurement

Suspect L1i pressure or branch issues? Measure — don't guess:

- `perf stat -e L1-icache-load-misses,branch-misses ./binary`
- `perf record -e iTLB-load-misses,L1-icache-load-misses ./binary` + `perf report` for hot-symbol attribution.
- Intel VTune, AMD uProf, or `linux-perf` flame graphs for visual inspection.
- Compiler reports: `-fopt-info-loop-vec`, `-Rpass=loop-unroll`, `-Rpass-missed=inline`.
