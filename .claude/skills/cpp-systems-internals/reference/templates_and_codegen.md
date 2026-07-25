# Templates and Code Generation

## Templates as blueprints

A template is a parameterized blueprint. It emits no machine code until **instantiated** by the compiler with concrete arguments.

```cpp
template <typename T>
T get_max(T a, T b) { return (a > b) ? a : b; }
```

When the compiler sees `get_max(10, 20)`:

1. **Template Argument Deduction** infers `T = int`.
2. The body is copied with `T` substituted by `int`.
3. A concrete `get_max<int>(int, int)` is emitted into the AST and object file.

### Template flavors

- **Function templates** — generic algorithms.
- **Class templates** — generic types (e.g., `std::vector<T>`).
- **Non-Type Template Parameters (NTTP)** — compile-time constant values. Allowed: integral, enum, pointer-to-object/function, lvalue reference, and (C++20) literal class types.

```cpp
template <typename T, std::size_t N>
class FixedArray { T data[N]; };   // N is a fixed compile-time size
```

## Compilation mechanics

Templates require full structural validation at instantiation, so definitions must live in headers, not split into `.cpp` files.

1. **Parse** — syntactic correctness; type-dependent expressions deferred.
2. **Implicit instantiation** — each translation unit (TU) that uses a specialization emits its own copy into its object file.
3. **ODR deduplication** — the linker discards duplicate symbols across object files, keeping exactly one definition under the One Definition Rule's template exemption.

## Risks: code bloat and compile-time cost

- **Compile time** — every TU that touches a template re-parses and re-instantiates it. Deeply templated code compiles slowly.
- **Binary size** — a 5 KB template instantiated for 20 distinct types contributes 100 KB of machine code. This expansion drives L1 instruction cache pressure — see `cpu_pipelines_and_l1i.md`.

### Mitigations

- **Thin Template pattern** — keep type-dependent code in the template; push type-independent code into a non-templated base. See `cpu_pipelines_and_l1i.md`.
- **`extern template`** — declare specializations as instantiated elsewhere, compiled exactly once. See `linkage_and_extern.md`.
- **Type erasure** — `std::function`, `std::any`, or pImpl when polymorphism cost is acceptable.

## Concepts (C++20)

Pre-C++20, templates relied on substitution failure ("duck typing"): if a type happened to support the required operations it compiled; otherwise the compiler produced multi-page diagnostics from deep inside the template.

**Concepts** lift constraints to the call site, so failures are checked and reported there:

```cpp
#include <concepts>

template <typename T>
requires std::integral<T> || std::floating_point<T>
T add(T a, T b) { return a + b; }
```

Abbreviated form:

```cpp
template <std::integral T>
T add(T a, T b) { return a + b; }
```

Benefits: cleaner overloading, much faster failure diagnostics, self-documenting interfaces, and constraints visible in IDE tooling.

## Auditing template footprint

- `nm --print-size --size-sort binary | c++filt` — list symbols by emitted size; spot bloated specializations.
- `objdump -d binary | c++filt` — confirm one copy per specialization survives the linker.
- `-ftime-report` (GCC/Clang) — see where compile time is spent.
- `-fmodules-ts` / C++20 modules — drastically reduce header reparse cost when supported.
