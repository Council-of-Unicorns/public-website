# Memory Mapping (`mmap`)

Practical guide for implementing and reviewing code that uses memory-mapped files and anonymous mappings. Linux/POSIX is the primary target; macOS and Windows differences are called out where they matter.

## Doctrine

Memory mapping is the kernel handing your process **direct access to its page cache**. You give up explicit `read`/`write` calls in exchange for on-demand paging, copy-on-write, optional cross-process sharing, and (often) zero-copy reads. The cost is a sharper class of failure modes if you mismanage lifetimes — SIGBUS on truncation, torn shared writes, durability surprises.

**Use mmap when:**
- The data is large and random-access (parsers, indexes, databases, model weights).
- Multiple processes need to share a region (ring buffers, IPC, lock-free queues).
- You want zero-copy reads against the kernel's page cache.
- You need anonymous memory at page granularity (custom allocators, guard pages).

**Avoid mmap when:**
- Files are small (sub-page); `read()` is simpler and competitive.
- Access is purely sequential and one-shot; `read()` plus `posix_fadvise(FADV_SEQUENTIAL)` wins.
- The file lives on a network filesystem (NFS, SMB) — page-cache semantics are not portable across the network and can corrupt silently.
- The file might be truncated during the mapping's lifetime — SIGBUS hazard.
- Address space is precious (32-bit processes; embedded MMU-constrained targets).

## The mechanical model

A successful `mmap()` returns a virtual address range backed by **pages** (4 KiB by default; 2 MiB / 1 GiB with huge pages). Pages are not necessarily resident — the kernel installs them on demand via the **page fault** path:

1. CPU touches an unmapped or non-resident page → page fault.
2. Kernel page-fault handler:
   - **Minor fault** — page is in the page cache; install a PTE and resume.
   - **Major fault** — page must be read from disk; block on I/O, then install and resume.
3. Execution resumes after the fault.

For file-backed mappings, the page cache *is* the storage. Reads of mapped pages and `read()` against the same file share the same cached pages. Writes through a `MAP_SHARED` mapping mark pages dirty; the kernel writes them back on its normal schedule unless you force it with `msync()`.

For `MAP_PRIVATE`, writes trigger **copy-on-write**: a private page is allocated, the data is copied, and the PTE switches to the private copy. Other processes — and `read()` callers — keep seeing the original. Writes through `MAP_PRIVATE` are local and are silently lost when the mapping is released.

## Flags and modes

### `prot` — protection

- `PROT_READ`, `PROT_WRITE`, `PROT_EXEC`, `PROT_NONE`.
- `PROT_NONE` is useful for guard pages and reserving address space without committing memory.
- Be as restrictive as possible. Read-only data should never be mapped with `PROT_WRITE`.

### `flags` — mapping kind

| Flag | Effect |
|---|---|
| `MAP_PRIVATE` | Copy-on-write; writes do not propagate to file or other processes. |
| `MAP_SHARED` | Writes go back to the file and are visible to other mappers. |
| `MAP_ANONYMOUS` | No backing file; zero-filled on first touch. Combine with `MAP_PRIVATE` for heap-like memory, `MAP_SHARED` for fork-shared regions. |
| `MAP_FIXED` | Force this exact address; overwrites any existing mapping. Almost always a bug. |
| `MAP_FIXED_NOREPLACE` | Linux 4.17+. Safer: fails instead of overwriting. |
| `MAP_POPULATE` | Linux. Prefault all pages at mmap time; trades startup latency for steady-state predictability. |
| `MAP_HUGETLB` / `MAP_HUGE_2MB` / `MAP_HUGE_1GB` | Use explicit huge pages. |
| `MAP_NORESERVE` | Don't reserve swap; OOM access SIGSEGVs instead of stalling. |
| `MAP_STACK` | Hint for thread stacks. |

### Common combinations

- **Anonymous private heap**: `MAP_PRIVATE | MAP_ANONYMOUS`.
- **Read-only file**: `MAP_PRIVATE` with `PROT_READ`.
- **Shared file**: `MAP_SHARED` with `PROT_READ | PROT_WRITE`.
- **Shared across fork()**: `MAP_SHARED | MAP_ANONYMOUS`, mapped before forking.

## Performance tuning

### `madvise()` — tell the kernel your access pattern

| Hint | Use for |
|---|---|
| `MADV_SEQUENTIAL` | Streaming reads; kernel does aggressive readahead and drops pages behind. |
| `MADV_RANDOM` | Random access; disables readahead. |
| `MADV_WILLNEED` | Prefault pages now; reduces major faults on next access. |
| `MADV_DONTNEED` | Release pages immediately. File pages drop; anonymous private pages zero on next access — a common allocator-reuse trick. |
| `MADV_FREE` | Lazy release for anonymous pages; reclaimed under memory pressure. |
| `MADV_HUGEPAGE` / `MADV_NOHUGEPAGE` | Opt the range into or out of transparent huge pages. |

### Huge pages

For very large mappings (gigabytes), 4 KiB pages cause TLB pressure. Two options:

- **Transparent Huge Pages (THP)** — automatic; controlled system-wide by `/sys/kernel/mm/transparent_hugepage/enabled` and per-mapping with `MADV_HUGEPAGE`.
- **Explicit hugetlb** — `MAP_HUGETLB`; requires reserved hugepages in `/proc/sys/vm/nr_hugepages`. More setup; more predictable.

### Prefaulting

By default, mapping is lazy: the first access to each page faults. For latency-sensitive code, prefault with `MAP_POPULATE` or `madvise(MADV_WILLNEED)` followed by touching every page. Trade-off: longer mmap-time cost; no major faults during the hot loop.

### Durability — `msync()`

For `MAP_SHARED`, writes are not persisted until the kernel writes the page back.

```c
msync(addr, length, MS_SYNC);    // synchronous; returns when written
msync(addr, length, MS_ASYNC);   // schedule writeback; returns immediately
msync(addr, length, MS_INVALIDATE); // invalidate other mappings of same file
```

For crash-consistent storage (databases, WAL files), `MS_SYNC` is required at every durability boundary. For best-effort caches, you can rely on the kernel's normal writeback cadence (`vm.dirty_writeback_centisecs`).

## Safety hazards

- **SIGBUS on file truncation** — if the backing file is truncated below the mapped region, touching the now-invalid pages raises SIGBUS. Either guarantee no truncation, or install a SIGBUS handler.
- **Writes past EOF** — writing through a writable shared mapping past EOF can SIGBUS. Always `ftruncate()` the file to the target size *before* mapping for writable shared mappings.
- **`MAP_FAILED`, not `NULL`** — the failure return is `(void*)-1`. Comparing against `NULL` silently passes errors through.
- **Address-space exhaustion** — on 32-bit, ~3 GiB usable; a few large mappings exhaust it. Even on 64-bit, fragmentation matters for long-lived processes that map and unmap heavily.
- **File handle lifetime** — on POSIX, `close(fd)` after `mmap()` is fine; the mapping holds its own reference. Windows is different: see the cross-platform section.
- **`munmap()` boundaries** — must pass an address from a prior `mmap()` and a length matching a contiguous mapping. Partial unmaps split mappings (which is sometimes intentional, often a bug).
- **Concurrent writers** — `MAP_SHARED` between threads or processes without synchronization → torn reads on values larger than a word. Use atomics for small values; mutexes/futexes for larger structures.
- **`fork()` interaction** — `MAP_PRIVATE` pages are COW'd into the child; `MAP_SHARED` is shared with the child. Anonymous `MAP_PRIVATE` mapped before fork is effectively shared until first write (then COW per page).
- **`mremap()`** — Linux-specific. Lets you grow, shrink, or move mappings. Pointers into the mapping must be assumed invalidated after a move.
- **`PROT_WRITE | PROT_EXEC`** — W^X violations are blocked by hardened kernels (`mprotect` will fail) and trigger code-signing mitigations on macOS/Windows.

## Common patterns

### Read-only file mapping (parser / index)

```c
int fd = open(path, O_RDONLY);
struct stat st; fstat(fd, &st);
void* base = mmap(NULL, st.st_size, PROT_READ, MAP_PRIVATE, fd, 0);
if (base == MAP_FAILED) { /* handle */ }
close(fd);   // mapping holds its own reference

// ... use base as a contiguous read-only buffer ...

munmap(base, st.st_size);
```

RAII wrapper (always wrap mappings to avoid leaks on exceptions):

```cpp
class ReadOnlyMapping {
    void* base_ = MAP_FAILED;
    std::size_t size_ = 0;
public:
    [[nodiscard]] static std::optional<ReadOnlyMapping> open(std::string_view path);

    std::span<const std::byte> bytes() const noexcept {
        return {static_cast<const std::byte*>(base_), size_};
    }

    ~ReadOnlyMapping() {
        if (base_ != MAP_FAILED) ::munmap(base_, size_);
    }

    ReadOnlyMapping(ReadOnlyMapping const&) = delete;
    ReadOnlyMapping& operator=(ReadOnlyMapping const&) = delete;
    ReadOnlyMapping(ReadOnlyMapping&& other) noexcept;
    ReadOnlyMapping& operator=(ReadOnlyMapping&& other) noexcept;
};
```

### Anonymous private region (custom allocator)

```c
void* arena = mmap(NULL, kArenaSize,
                   PROT_READ | PROT_WRITE,
                   MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
```

Useful for arena/pool allocators, large transient buffers, and guard-paged stacks.

### Shared anonymous (parent ↔ child)

Map shared before fork:

```c
void* p = mmap(NULL, kRegionSize,
               PROT_READ | PROT_WRITE,
               MAP_SHARED | MAP_ANONYMOUS, -1, 0);
// fork() — both processes now access the same physical pages
```

For unrelated processes, use `shm_open()` + `mmap`:

```c
int shm = shm_open("/my_region", O_RDWR | O_CREAT, 0600);
ftruncate(shm, kRegionSize);
void* p = mmap(NULL, kRegionSize, PROT_READ | PROT_WRITE, MAP_SHARED, shm, 0);
```

### Ring buffer with double-mapping

Map the same physical region twice consecutively; reads and writes that cross the end wrap automatically without a branch. Common in audio, networking, lock-free queues:

```c
int fd = memfd_create("ring", 0);
ftruncate(fd, size);
void* first  = mmap(NULL,     size, PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0);
void* second = mmap((char*)first + size, size, PROT_READ|PROT_WRITE,
                    MAP_SHARED | MAP_FIXED, fd, 0);
// Now writing past 'first[size-1]' lands in second[0], which is the same page.
```

## Anti-patterns

- mmap of sub-page files — overhead exceeds savings.
- mmap on NFS / SMB / FUSE — page-cache semantics are not network-safe.
- Holding a mapping while truncating the file — SIGBUS.
- Forgetting `munmap()` — process exit reclaims it, but long-running daemons leak address space.
- Treating `MAP_PRIVATE` writes as durable. They are not.
- Mapping with `PROT_EXEC` on writable memory.
- Relying on pages being resident without prefaulting — first-access latency in a critical section can be milliseconds.
- Cross-thread access to a mapping that may be `mremap()`-ed — invalidates all pointers without warning.
- Using `MAP_FIXED` to "place data at a nice address" — destroys whatever is currently mapped there.

## Cross-platform

- **Linux** — `mmap` / `munmap` / `madvise` / `mremap` / `msync`. Richest flag set. `memfd_create` for anonymous backing files. `userfaultfd` for handling faults in userspace.
- **macOS / BSD** — POSIX `mmap`; **no `mremap`**. Use `posix_madvise` instead of `madvise`. Mach VM underneath; `mach_vm_*` for advanced cases.
- **Windows** — `CreateFileMapping` + `MapViewOfFile` + `UnmapViewOfFile`. Two-step model: the **section** (mapping object) and the **view** (mapped address) are separate kernel objects. The section can persist after the view is unmapped. Use `FlushViewOfFile` for durability. `VirtualAlloc` for anonymous mappings.
- **Cross-platform wrappers** — `boost::interprocess::file_mapping` / `mapped_region` (heavy but complete); `mio` (C++17 header-only); Rust `memmap2`; Python `mmap`; Go `golang.org/x/exp/mmap`.

## Cross-language

The same syscall, the same semantics — only the wrapper changes.

- **Python**: `mmap.mmap(fileno, length, access=mmap.ACCESS_READ)`. The page cache, page faults, and durability rules are identical. `numpy.memmap` adds typed access for numeric arrays. `multiprocessing.shared_memory` wraps `shm_open` + `mmap`.
- **Rust**: `memmap2::Mmap` / `MmapMut`. Inherently unsafe at the boundary because the mapping can be truncated or unmapped under safe references — read the crate's safety docs. Prefer `Mmap` (read-only) where possible.
- **Go**: rare in idiomatic Go; GC and goroutine stacks reduce the natural use cases. `golang.org/x/exp/mmap` for read-only; raw syscalls for advanced cases. Go's GC does **not** move mmap'd memory, so pointers into it are stable.
- **Java / JVM**: `FileChannel.map()` returns `MappedByteBuffer`. JIT cannot inline through it. Direct-buffer leaks are a perennial production issue — `Cleaner` or `Unsafe.invokeCleaner` for explicit release. C++ FFI must respect alignment.

## Code review checklist

For any change that uses `mmap`, verify:

- [ ] Return value compared against `MAP_FAILED`, not `NULL`.
- [ ] The mapping is released on all exit paths — RAII, `defer`, `try/finally`, or a documented owning scope.
- [ ] File handle lifetime is correct for the platform (POSIX: can close immediately; Windows: section vs view).
- [ ] The file size is fixed during the mapping's lifetime, or truncation is explicitly defended against.
- [ ] `MAP_PRIVATE` vs `MAP_SHARED` matches the caller's actual durability and visibility intent. Writes through `MAP_PRIVATE` are local and silently discarded.
- [ ] For shared mappings: durability boundaries are handled with `msync(MS_SYNC)` (or `FlushViewOfFile` on Windows).
- [ ] For shared mappings between threads or processes: concurrent access is correctly synchronized. Atomics for small values; locks for compound state.
- [ ] Large mappings carry sensible `madvise()` hints (`SEQUENTIAL` / `RANDOM` / `WILLNEED`).
- [ ] Latency-sensitive hot paths prefault (`MAP_POPULATE` or explicit touch loop) to avoid major faults inside the critical section.
- [ ] Address-space exhaustion considered on 32-bit or constrained targets.
- [ ] Backing storage is a local filesystem, not NFS / SMB.
- [ ] `mremap()` callers reset *all* pointers into the region after a move.
- [ ] `PROT_*` is as restrictive as possible; no `PROT_WRITE` on read-only data, no `PROT_EXEC` on writable memory.
- [ ] If the mapping holds untrusted data (parsing files from disk): bounds and integrity are still validated. Mapped data is still untrusted input.
- [ ] Mapping size is page-aligned where the API requires it (`getpagesize()` / `sysconf(_SC_PAGESIZE)`).

## Verification and observability

| Goal | Command |
|---|---|
| Inspect a process's mappings | `cat /proc/<pid>/maps` or `pmap <pid>` |
| Per-mapping memory accounting | `cat /proc/<pid>/smaps` — Rss, Pss, Shared/Private clean/dirty |
| Page-fault counts | `perf stat -e page-faults,minor-faults,major-faults ./bin` |
| Trace mmap-related syscalls | `strace -e mmap,munmap,madvise,msync,mremap ./bin` |
| Dynamic tracing | `bpftrace -e 'tracepoint:syscalls:sys_enter_mmap { @[comm] = count(); }'` |
| Check which pages are resident | `mincore(addr, length, vec)` |
| Huge page status | `grep AnonHugePages /proc/<pid>/smaps`; `cat /sys/kernel/mm/transparent_hugepage/enabled` |
| System-wide paging pressure | `vmstat 1` — watch `pswpin`/`pswpout`, `si`/`so` |
| Sanitizer interaction | AddressSanitizer tracks mmap regions and flags OOB; UBSan flags misaligned reads. |

Performance claims about mmap vs `read`/`write` must be measured on the actual workload. Often `pread()` wins for streaming; mmap wins for repeated random access against the page cache. Don't choose by folklore — see the verification discipline in the `principal-production-engineer` skill.
