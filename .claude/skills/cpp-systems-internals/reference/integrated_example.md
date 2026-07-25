# Integrated Example — Concepts + Thin Template + `alignas` + `extern template`

A single component that demonstrates how the techniques in this skill compose. Each annotation links back to the underlying mechanism.

```cpp
// ============================================================
// interface.hpp
// ============================================================
#pragma once
#include <new>
#include <concepts>

// Concept: compile-time type constraint. Failures report at the call
// site, not deep in the template body.  See templates_and_codegen.md.
template <typename T>
concept Numeric = std::integral<T> || std::floating_point<T>;

// Thin Template: type-independent logic in a non-templated base class,
// compiled exactly once. Keeps L1i pressure bounded across many
// specializations.  See cpu_pipelines_and_l1i.md.
class MatrixProcessorBase {
protected:
    int dimensions;
    void execute_hardware_handshake();   // defined in .cpp; emitted once
};

// Type-dependent shell — minimal, easily inlined.
template <Numeric T>
class ThreadSafeMatrix : public MatrixProcessorBase {
public:
    // alignas: each contended field gets its own cache line, eliminating
    // false sharing under MESI.  See cache_lines_and_alignment.md.
    alignas(std::hardware_destructive_interference_size) T primary_worker_cell;
    alignas(std::hardware_destructive_interference_size) T secondary_worker_cell;

    void calculate_bounds() {
        // Small, type-specific. Inlineable; no virtual dispatch.
        primary_worker_cell += 2;
    }
};

// extern template: do NOT implicitly instantiate ThreadSafeMatrix<int>
// in every TU that includes this header. The definition lives in
// interface.cpp.  See linkage_and_extern.md.
extern template class ThreadSafeMatrix<int>;
```

```cpp
// ============================================================
// interface.cpp
// ============================================================
#include "interface.hpp"
#include <iostream>

void MatrixProcessorBase::execute_hardware_handshake() {
    // Single, shared definition. Stays resident in L1i across all
    // ThreadSafeMatrix<T> specializations.
    std::cout << "Initializing system matrices...\n";
}

// Explicit instantiation definition — emit ThreadSafeMatrix<int> code
// exactly once, here. All other TUs reference this symbol.
template class ThreadSafeMatrix<int>;
```

## What each technique buys you

| Technique | Mechanism | Effect |
|---|---|---|
| `Numeric` concept | Compile-time constraint at the call site | Fast, clear failure diagnostics |
| `MatrixProcessorBase` | Thin Template pattern | Type-independent code emitted once; bounded L1i pressure |
| `alignas(...)` on hot fields | Cache-line isolation | No false sharing under concurrent writes |
| `extern template class ThreadSafeMatrix<int>` | Linker-coordinated explicit instantiation | One copy in the binary; faster compiles |
| `final` on closed types (not shown) | Devirtualization opportunity | Direct calls and inlining preserved |

## Verification — audit, do not guess

When applying these techniques in production, measure:

- **Binary size and symbols** — `objdump -d`, `readelf -s`, `nm --print-size --size-sort` to confirm one copy of each specialization and one copy of base code.
- **L1i misses / branch mispredictions** — `perf stat -e L1-icache-load-misses,branch-misses ./bin`.
- **False sharing** — `perf c2c` (Linux) for cache-line contention events with source-line attribution.
- **Compile time deltas** — measure before/after introducing `extern template` and Concepts; record results in the PR description.

Performance claims without measurement are folklore. See the `principal-production-engineer` skill's verification discipline.
