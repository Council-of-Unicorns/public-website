# Linkage, Translation Units, and `extern`

## The compilation pipeline

C++ source compiles one **translation unit** at a time:

1. **Preprocessor** — reads a `.cpp` file, expands macros, evaluates `#ifdef`, splices in every `#include`'d header. Produces a flattened text stream.
2. **Translation Unit** — the post-preprocessor text. The compiler parses one TU at a time and emits one object file (`.o` / `.obj`).
3. **Linker** — combines object files, resolves symbolic references, fixes up addresses, produces an executable or library.

## Linkage classes

- **No linkage** — block-scoped names (locals, parameters).
- **Internal linkage** — visible only within the TU. Achieved with `static` at namespace scope or via an anonymous namespace.
- **External linkage** — visible across TUs. The linker resolves a use in one TU against a definition in another.

## `extern`: declaration vs definition

`extern` separates a symbol's **declaration** (a name and type, no storage allocated) from its **definition** (the point where storage or code is emitted).

### Context 1: Global variables

```cpp
// common.hpp
#pragma once
extern int global_system_state;   // declaration only — no storage

// common.cpp
#include "common.hpp"
int global_system_state = 100;    // definition — storage allocated here
```

Omitting `extern` in the header would define the variable in every TU that includes it → duplicate-symbol error at link time.

### Context 2: `extern template` (C++11)

To prevent every TU from instantiating the same template specialization, declare it `extern` and define it exactly once:

```cpp
// network.hpp
template <typename T>
class Packet { public: void serialize() {} };

extern template class Packet<int>;   // "do not implicitly instantiate here"
```

```cpp
// network.cpp
#include "network.hpp"
template class Packet<int>;          // explicit instantiation — emit code exactly once
```

All other TUs now insert a reference token that the linker resolves to the single definition in `network.cpp`. This cuts compile time and avoids redundant codegen across the binary.

### Context 3: `extern "C"`

C++ **mangles** function names to encode argument types (e.g., `void print(int)` → `_Z5printi`) — this is what enables overloading. C does not mangle.

`extern "C"` disables mangling so a C++ TU can link against C symbols:

```cpp
extern "C" {
    void standard_c_kernel_call(int descriptor);   // emitted with unmangled name
}
```

Use for: C library headers, syscall wrappers, `dlsym`/`GetProcAddress` lookups, and any ABI boundary where the consumer expects a plain C symbol.

## When the linker complains

- **Multiple definition** — a definition appeared in more than one TU. Move it behind `extern`, mark it `inline` (header-only), or wrap in an anonymous namespace if it should be TU-local.
- **Undefined reference** — a declaration exists but no TU defines the symbol. Check that the definition's TU is compiled and included in the link line.
- **Mangled-name mismatch** — usually a missing `extern "C"` when calling a C function from C++, or a header/library version skew.

## Auditing

- `nm --demangle binary` — list defined and undefined symbols.
- `readelf -s binary` — symbol table with linkage attributes.
- `objdump -t binary` — raw symbol table including section info.
- Linker map files (`-Wl,-Map=out.map`) — see exactly which TU contributed each symbol.
