---
name: cpp-systems-internals
description: C++-specific reference for runtime mechanics, API design, data-oriented performance, and OS-level memory. Use when writing or reviewing C++ where hardware behavior, codegen cost, ownership vocabulary, API style, or kernel paging behavior matters — lambdas, templates, linkage, CPU pipeline / L1i, cache lines and false sharing, vtables and devirtualization, static vs dynamic linking, smart pointers / spans / arenas, `[[nodiscard]]` / `noexcept` / `Result<T, E>`, AoS/SoA / ECS / vectorization-friendly layouts, and memory-mapped files (`mmap`, `madvise`, durability, hazards). Each topic is a separate reference file; load only what is relevant. Routed to from `principal-production-engineer`.
---

# C++ Systems Internals

Reference material for the runtime mechanics that govern C++ performance and correctness at the systems level. Each topic below has its own reference file; load only what is relevant to the current task.

## When to use

- Writing or reviewing C++ code where hardware behavior matters (hot paths, real-time, parsers, networking, allocators).
- Diagnosing performance puzzles whose root cause is cache, pipeline, or codegen behavior.
- Making structural decisions about templates, polymorphism, or linkage.
- Explaining *why* a specific C++ construct behaves as it does at the binary/CPU level.

Pair with `principal-production-engineer` for doctrine ("what to prefer") and workflow ("how to implement and verify"). This skill answers "what does the machine actually do." For the cross-language performance doctrine, optimization order, layout/branchless/SIMD/bit-packing playbook, and measure-first protocol that *uses* these mechanics, load `data-oriented-design`.

## Reference index — progressive disclosure

Load only the files relevant to the current question.

### Design — layout and structure

- **[reference/data_oriented_design.md](reference/data_oriented_design.md)** — dense containers, AoS vs SoA, indices over pointers, generational handles, pools/arenas, plain structures over hierarchies, vectorization-friendly control flow, hot/cold split, ECS patterns, anti-patterns, and the verification commands that prove a layout is actually faster.

### API and ownership

- **[reference/cpp_api_style.md](reference/cpp_api_style.md)** — `[[nodiscard]]`, `noexcept`, `Result<T, E>`, naming conventions, avoiding exception smuggling, invariant-in-types, production API checklist.
- **[reference/cpp_ownership_and_arenas.md](reference/cpp_ownership_and_arenas.md)** — ownership vocabulary (smart pointers, references, spans), smart-pointer policy, arena patterns, memory-safety rules, sanitizer setup.

### Codegen and the language model

- **[reference/lambdas_and_closures.md](reference/lambdas_and_closures.md)** — λ-calculus foundation, closure-type code generation, capture semantics, performance.
- **[reference/templates_and_codegen.md](reference/templates_and_codegen.md)** — template instantiation, ODR, compile-time cost, binary bloat, Concepts (C++20).
- **[reference/linkage_and_extern.md](reference/linkage_and_extern.md)** — translation units, linkage classes, `extern` for globals / templates / `"C"`.
- **[reference/vtables_and_polymorphism.md](reference/vtables_and_polymorphism.md)** — vptr/vtable layout, dispatch sequence, performance cost, devirtualization.

### Hardware and CPU behavior

- **[reference/cpu_pipelines_and_l1i.md](reference/cpu_pipelines_and_l1i.md)** — pipeline stages, hazards, branch prediction, L1i churning, the Thin Template pattern.
- **[reference/cache_lines_and_alignment.md](reference/cache_lines_and_alignment.md)** — 64-byte cache lines, spatial locality, false sharing, `alignas`/`alignof`, MESI bouncing.

### Operating system and I/O

- **[reference/memory_mapping.md](reference/memory_mapping.md)** — practical `mmap` guide: when to use and when not, page-fault model, `MAP_PRIVATE`/`MAP_SHARED`/anonymous, `madvise` and huge-page tuning, durability with `msync`, hazards (SIGBUS, truncation, address-space exhaustion), common patterns (RAII wrapper, anonymous arena, shared anonymous, ring buffer), anti-patterns, cross-platform notes, code-review checklist, verification commands.

### Linking and deployment

- **[reference/static_vs_dynamic_linking.md](reference/static_vs_dynamic_linking.md)** — `.a`/`.so` tradeoffs, PLT/GOT indirection, deployment scenarios.

### Capstone

- **[reference/integrated_example.md](reference/integrated_example.md)** — Concepts + Thin Template + `alignas` + `extern template` combined into one optimized component, with verification commands.

## How to apply this material

When a question touches a topic here:

1. State the concrete mechanism — what the compiler / linker / CPU is doing.
2. State the implication for the code under discussion — correctness, performance, footprint.
3. Cite the structural fact, not folklore — these references give you the citations.
4. When recommending an optimization, also state the measurement (`perf`, `objdump`, `nm`, VTune) that would validate or falsify it.
