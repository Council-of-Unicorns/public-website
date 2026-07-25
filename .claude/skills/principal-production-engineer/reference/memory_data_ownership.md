# Data Layout, Locality, and Ownership

Language-agnostic principles for shaping data and reasoning about lifetimes. For C++ syntax (smart pointers, spans, arenas, sanitizers), load the `cpp-systems-internals` skill and read `reference/cpp_ownership_and_arenas.md`. For C++ cache and codegen behavior, see the rest of that skill.

## Doctrine

Dense data. Explicit ownership. Visible failure. No hidden allocation. No unnecessary indirection.

## Data-oriented programming

Do not model the world. Model the computation.

Start with:

- What data exists?
- How is it transformed?
- What fields are touched together?
- What is hot vs cold?
- What operations are batched?
- What lifetimes exist?
- What can be IDs/indices instead of pointers/references?

Object-first design asks for nouns. Data-oriented design asks for access patterns.

## Dense memory representation

Prefer contiguous, index-addressable structures. Be suspicious of pointer graphs, deep object hierarchies, and per-element dispatch in hot loops.

| Language | Prefer (dense) | Treat as expensive |
|---|---|---|
| C++ | `std::array`, `std::vector`, `std::span`, arena-backed buffers, struct-of-arrays | `std::list`, `std::map` in hot paths, `vector<unique_ptr<T>>`, deep inheritance graphs |
| Python | `numpy` arrays, `array.array`, `bytes`/`bytearray`, dataclasses with `__slots__`, structured arrays, `polars`/`pyarrow` | `list[object]` of heterogeneous types, dicts on the hot path, deeply nested object trees, per-element Python-level loops |
| Rust | `Vec<T>`, `&[T]`, `Box<[T]>`, `SmallVec` | `Vec<Box<T>>`, `HashMap` in inner loops, `dyn Trait` in tight loops |
| Go | slices, fixed-size arrays, struct-of-slices | linked structures, `map` in hot paths, interface dispatch in inner loops |

Rule of thumb: arrays until proven otherwise.

## AoS vs SoA

Array-of-structs is natural:

```text
particles = [(x, y, z, vx, vy, vz), ...]
```

Struct-of-arrays can be faster when hot loops touch one field across many records:

```text
particles.x   = [...]
particles.y   = [...]
particles.vx  = [...]
```

- C++: separate `std::vector<float>` per field.
- Python: separate `numpy.ndarray` per field — and almost always vectorize with `numpy`/`numba`/`cython` rather than looping in Python.
- Rust: separate `Vec<f32>` per field; the `soa-derive` crate automates it.

Rule: fields accessed together should live together; fields accessed separately should not be forced together.

## Hot / cold split

**Hot path:** no hidden allocation, no exceptions, limited locks, compact data, predictable branches, direct calls, batched operations, minimal logging, bounded work.

**Cold path:** rich diagnostics, formatting, dynamic allocation if acceptable, maps/strings/config parsing, human-readable error context, slow recovery and reporting.

Separate hot operational fields from cold diagnostic metadata. In Python, this means: keep frequently-accessed attributes simple and `__slots__`'d; push diagnostic context into separate structures or lazy properties; avoid `__repr__`/logging in inner loops.

## Batching

Prefer batch APIs for hot paths. Batching reduces syscalls, locks, branches, cache misses, and repeated setup cost.

- C++: `Status process_batch(PacketBatch batch, Arena& scratch) noexcept;`
- Python: operate on whole `numpy` arrays / `pandas` columns / `polars` series; avoid per-element Python-level loops; use vectorized operators or `numba`/`cython` when the algorithm cannot vectorize.
- Rust: prefer iterator chains over manual loops; let the compiler fuse them.

## Fusion vs pipelining — when a multi-stage service should keep stages local

If a service has multiple logical stages (e.g., parse → compute candidates → optimize), the default is to **fuse them in one process, often in one function**, so intermediate data stays request-local, hot, and short-lived. Pipelining — putting queues and workers between stages — trades that locality for concurrency, extends intermediate-object lifetimes, and can promote queue-resident data into older GC generations or push it out of L1/L2.

Pipeline only when concurrency clearly wins: different bottleneck resources per stage, naturally streaming work, different batch sizes per stage, or operational isolation. Otherwise fuse, prune candidates early, and batch within a stage.

For the full decision criteria, queue/backpressure/representation standards, language-specific failure modes (managed-runtime GC promotion vs native allocator/cache pressure), required metrics, and a fused-vs-pipelined baseline comparison procedure, see [reference/pipeline_design.md](reference/pipeline_design.md).

## Ownership and lifetime — universal concept

Every value has:

- an **owner** — the entity responsible for releasing it;
- a **lifetime** — the interval over which it remains valid;
- a **scope** — where it can be accessed.

Make all three obvious at API boundaries. Ambiguous ownership is the source of dangling references, double-frees, leaks, and unsafe concurrency — in every language.

Universal questions to answer when designing an interface:

- Who owns this value?
- Who can mutate it, and when?
- Until when is it valid?
- What happens if a reference outlives its source?
- What does cleanup look like, and who runs it?

### Language-specific syntax

| Concern | C++ | Python | Rust | Go |
|---|---|---|---|---|
| Unique ownership | `std::unique_ptr<T>` | object reference (GC) | `Box<T>`, owned `T` | value type, pointer to local |
| Required borrow | `T&` | object reference (caller must not mutate during iteration) | `&T`, `&mut T` | pointer to value |
| Borrowed range | `std::span<T>` | memoryview, numpy view | `&[T]` | slice header |
| Shared lifetime | `std::shared_ptr<T>` (only when truly shared) | normal ref (GC handles it) | `Arc<T>`, `Rc<T>` | shared via pointer + sync |
| Phase-scoped (arena) | custom arenas, `std::pmr` | context manager (`with`), explicit pools | `bumpalo`, `typed-arena` | `sync.Pool`, per-request allocators |
| External resource | RAII destructor | `with` statement, `__enter__`/`__exit__` | `Drop` trait | `defer` |

Python-specific guidance: prefer **context managers** (`with`) for resources with non-trivial lifetime — files, locks, transactions, DB connections, GPU streams, async tasks. Treat `__del__` as last-resort cleanup, not the primary mechanism — GC timing is not deterministic, and `__del__` is skipped on interpreter shutdown.

For complete C++ ownership syntax (smart pointer policy, arena rules, sanitizer setup), load the `cpp-systems-internals` skill and read `reference/cpp_ownership_and_arenas.md`.

## Memory mapping — when the OS owns the pages

Memory-mapped files let you treat a file as an in-process byte array, with the kernel managing residency through its page cache. Available everywhere — POSIX `mmap`, Windows `MapViewOfFile`, Python `mmap.mmap` / `numpy.memmap`, Rust `memmap2`, Java `FileChannel.map`. The mechanism enables zero-copy reads, on-demand paging, copy-on-write semantics, and cross-process shared memory — at the cost of a sharper class of failure modes.

**Consider mmap when:**
- The data is large and random-access (parsers, indexes, model weights, databases).
- Multiple processes share a region (ring buffers, IPC).
- You need anonymous memory at page granularity (custom allocators, guard pages).

**Avoid mmap when:**
- Files are small (sub-page) — `read()` is simpler and competitive.
- Access is purely sequential and one-shot — `read()` plus readahead hints usually wins.
- The file lives on a network filesystem (NFS, SMB) — page-cache semantics are unsafe.
- The file might be truncated during the mapping — SIGBUS hazard.

**Universal hazards** (apply in every language wrapper):

- **SIGBUS on truncation** — touching pages past a truncated EOF kills the process.
- **`MAP_PRIVATE` writes are not durable** — silently discarded on unmap.
- **Durability requires `msync` / `FlushViewOfFile`** — kernel writeback is asynchronous by default.
- **Cross-process / cross-thread concurrent access** is unsynchronized — atomics or locks required for non-trivial writes.
- **Address-space exhaustion** on 32-bit or constrained targets.
- **Mapping lifetime vs file handle lifetime** — platform-specific rules; get them wrong and the mapping becomes invalid.
- **Mapped data is still untrusted input** — bounds and integrity checks must still happen if the file is parsed.

For practical implementation patterns (RAII wrappers, anonymous arenas, shared anonymous regions, ring buffers), flag semantics, `madvise` / huge-page tuning, durability rules, cross-platform notes, the full **code-review checklist**, and verification commands (`/proc/<pid>/maps`, `perf`, `strace`, `mincore`), load the `cpp-systems-internals` skill and read `reference/memory_mapping.md`. The guide is C-syscall-centric but the semantics carry over to every language wrapper.

## Memory and lifetime hazards

Universal hazards (mapped to per-language manifestations):

- **Dangling reference / view outliving source**
  - C++: `span` into a destroyed `vector`; reference to local returned upward.
  - Python: iterator over a list that gets mutated; cached `memoryview` after the buffer is released.
  - Rust: caught by the borrow checker.
- **Iterator/view invalidation on resize or mutation**
  - C++: `vector` reallocation invalidates pointers/iterators/references.
  - Python: `RuntimeError: dictionary changed size during iteration`.
  - Rust: borrow checker rejects.
- **Use-after-free**
  - C++/Rust/Go (with `unsafe`): direct UB.
  - Python: closing a file then using its handle; `weakref` resurrection edge cases.
- **Concurrent unsynchronized mutation**
  - C++/Rust/Go: data races, partial writes, torn values.
  - Python: `asyncio` interleaving at await points; CPython GIL hides some races but not logical ones (compound state mutations).
- **Reinterpret without honoring alignment / endianness**
  - C++: `reinterpret_cast` over wire data; UB on misaligned access on some ISAs.
  - Python: `struct.unpack` with the wrong format string; `numpy.frombuffer` ignoring dtype.
- **Untrusted-data deserialization → arbitrary code execution**
  - C++: deserializing into types with virtual destructors and crafted pointers.
  - Python: `pickle.load` on untrusted input.

## Review questions

- Is the data layout shaped like the access pattern?
- Are hot and cold fields separated?
- Are arrays/slices/IDs possible instead of pointer graphs or dict graphs?
- Is ownership/lifetime visible at every API boundary?
- Can any borrow dangle or any iterator be invalidated?
- Is shared ownership justified by real shared lifetime — or is it ambiguity dressed up as policy?
- Are temporary allocations phase-based and explicit (arena, context manager, pool)?
- Does the hot path allocate, block, throw, log, or call dispatch unexpectedly?
- For each external resource (file, socket, lock, transaction): who closes it, and what happens on exception?
