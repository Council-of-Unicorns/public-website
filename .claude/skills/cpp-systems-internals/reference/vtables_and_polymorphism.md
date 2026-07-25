# Vtables and Runtime Polymorphism

## The blueprint

To implement virtual dispatch, the compiler injects two structures:

- **Vtable** — one per class with virtual functions. A static array of function pointers, indexed by the order of the class's virtual functions. Lives in read-only static memory.
- **Vptr** — one per object instance. A hidden pointer member (typically at offset 0) pointing to the class's vtable. Set by the constructor.

## Object layout

```cpp
class Base {
public:
    int base_var;
    virtual void step_one() {}
    virtual void step_two() {}
};

class Derived : public Base {
public:
    int derived_var;
    void step_one() override {}   // override; step_two inherited
};
```

Memory:

```
STATIC MEMORY (vtables)
====================================================================
Base vtable:     [0] → &Base::step_one
                 [1] → &Base::step_two

Derived vtable:  [0] → &Derived::step_one    (overridden slot)
                 [1] → &Base::step_two       (inherited slot)


RUNTIME (object instances)
====================================================================
Base instance:                        Derived instance:
+----------------------------+        +----------------------------+
| vptr → Base vtable         |        | vptr → Derived vtable      |
+----------------------------+        +----------------------------+
| base_var (4 bytes)         |        | base_var (4 bytes)         |
+----------------------------+        +----------------------------+
| [padding]                  |        | [padding]                  |
+----------------------------+        +----------------------------+
                                      | derived_var (4 bytes)      |
                                      +----------------------------+
```

## Dispatch sequence

```cpp
Base* poly = new Derived();
poly->step_one();
```

The compiler cannot resolve `step_one` at compile time, so it emits the indirection sequence:

1. Dereference `poly` → object header.
2. Load the hidden `vptr` from the header.
3. Index into the vtable at slot 0 (the compile-time-known offset for `step_one`).
4. Load the function pointer at that slot.
5. Indirect-call through that pointer, passing `poly` as the implicit `this`.

Conceptually: `(*poly->vptr[0])(poly);`

## Performance costs

- **Per-object overhead** — every virtual-bearing instance carries one extra pointer (8 bytes on 64-bit). For millions of small objects, this can double footprint and degrade L1d locality.
- **Indirect call latency** — two pointer dereferences (vptr load, function-pointer load) before the call. Each is a potential L1d miss.
- **Inlining blocked** — the compiler cannot inline a call whose target is resolved at runtime, which also blocks downstream optimizations (loop unrolling, constant propagation, vectorization).
- **Branch predictor pressure** — indirect calls go through the **indirect branch predictor**, which is less accurate than the direct branch predictor. Polymorphic call sites with high target variability mispredict heavily.

## Devirtualization

Modern optimizers can remove the indirection when the target is statically deducible:

- **Type-known site** — if escape analysis proves the dynamic type, the call becomes direct and inlinable.
- **`final` class** — explicit hint that no further override is possible:

  ```cpp
  class TargetFinal final : public Base {
  public:
      void step_one() override {}
  };
  ```

  A call to `step_one` through a `TargetFinal*` can be lowered to a direct call.

- **`final` method** — `void step_one() final;` prevents further overrides and allows devirtualization for static-type call sites.
- **LTO** — whole-program analysis dramatically expands devirtualization opportunities.

## When to avoid virtual dispatch

In hot paths with predictable dispatch targets, prefer:

- **`std::variant` + `std::visit`** for closed-set polymorphism (no vptr; dispatch can lower to a jump table or static dispatch).
- **CRTP** (Curiously Recurring Template Pattern) for compile-time polymorphism with full inlining.
- **Tagged unions** or enum-driven dispatch when the set is small and fixed.

Reserve `virtual` for genuinely open-set polymorphism with deep hierarchies and runtime extensibility (plugins, abstract domain interfaces, framework hooks).

## Auditing

- `objdump -d -C binary` — disassemble and demangle; look for indirect call instructions (`call *...`) at hot sites.
- `perf record -e branch-misses` followed by `perf annotate` on the hot symbol — surfaces mispredicted indirect calls.
- Compiler `-Rpass=devirt` (Clang) — confirms which calls were devirtualized.
