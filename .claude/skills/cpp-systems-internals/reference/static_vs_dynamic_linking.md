# Static vs Dynamic Linking

## The choice

At link time, external library code can be:

- **Statically linked** (`.a` / `.lib`) — copied into the executable; one self-contained binary.
- **Dynamically linked** (`.so` / `.dll` / `.dylib`) — referenced by name; resolved at load or call time against a shared library on the host system.

```
STATIC LINKING
=========================================================
[source.cpp] → [object.o] ──┐
                            ├──→ Linker → [self-contained executable]
[library.a]  ──────────────┘                (library code embedded)

DYNAMIC LINKING
=========================================================
[source.cpp] → [object.o] ──┐
                            ├──→ Linker → [slim executable] + [external .so]
[library.so] ──────────────┘               (executable contains references)
```

## Tradeoff matrix

| Dimension | Static (`.a` / `.lib`) | Dynamic (`.so` / `.dll`) |
|---|---|---|
| Binary size | Large — library code is copied in | Small — references only |
| RAM footprint | Per-process copy of library text | OS maps shared text once across processes |
| Deployment | Self-contained; no external deps | Requires correct library version on host |
| Patching | Recompile + redeploy the app | Replace `.so`; all consumers patched |
| Runtime | Direct calls; LTO across module boundaries | Calls go through PLT/GOT (one extra indirection) |
| Plugin extensibility | None | `dlopen` / `LoadLibrary` at runtime |

## When to choose static linking

- **Container images** — small, immutable, no dynamic loader needed at runtime. Common with musl-libc Go / Rust / C++ stacks.
- **Embedded systems** — bare-metal microcontrollers without a dynamic loader or filesystem.
- **Dependency isolation** — pin an exact library version inside the binary; survive system upgrades and dependency-hell on the host.
- **CLI tools shipped to mixed environments** — single drop-in executable.

## When to choose dynamic linking

- **OS-shipped libraries** — `libc`, Win32, Cocoa, Metal. Statically linking these would explode disk and RAM use across every binary on the system.
- **Plugin architectures** — DAWs, game engines, browsers, GPU drivers — load third-party modules at runtime via `dlopen` (POSIX) or `LoadLibrary` (Windows).
- **Closed-source vendor libraries** — no source to statically compile; link against the vendor's shipped `.so`/`.dll`.
- **Security patching cadence** — fix once in the shared library; every consumer benefits without re-deploying.

## Runtime indirection cost

A dynamic call passes through a **Procedure Linkage Table (PLT)** and **Global Offset Table (GOT)**:

- First call → lazy resolution; the dynamic linker patches the GOT entry.
- Subsequent calls → single indirect jump through the GOT.

Amortized cost is small (~1 extra cycle and a potential L1d miss on the GOT entry) but it does block inlining and cross-module LTO.

`-fvisibility=hidden` plus explicit export annotations (e.g., `__attribute__((visibility("default")))`) reduces exported symbol counts, speeds load time, and enables more aggressive optimization inside the library.

## Hybrid strategies

- **Partial static linking** — `-Wl,--whole-archive` to embed a specific `.a` while keeping the rest dynamic.
- **Static app + dynamic libc** — common in container images (avoids glibc-versus-musl ABI traps while keeping the app self-contained).
- **Bundled dynamic libraries** — ship the `.so` files alongside the binary with rpath set; gets dynamic linking's patchability without depending on the host system's library versions.

## Auditing

- `ldd binary` — list dynamic dependencies and their resolution paths.
- `readelf -d binary` — view the dynamic section: SONAME, RPATH/RUNPATH, NEEDED entries.
- `nm -D binary` — dynamic symbol table.
- `objdump -p binary` — full program headers including dynamic linkage info.
- `LD_DEBUG=bindings ./binary` — trace dynamic symbol resolution at runtime.
