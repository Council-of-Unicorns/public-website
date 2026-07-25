# Data-Oriented Design in C++

Practical patterns for densely-represented, simply-structured, predictably-flowing C++ code. Pairs with [`cache_lines_and_alignment.md`](cache_lines_and_alignment.md) (hardware), [`cpu_pipelines_and_l1i.md`](cpu_pipelines_and_l1i.md) (codegen-and-cache), [`vtables_and_polymorphism.md`](vtables_and_polymorphism.md) (dispatch costs). For the language-agnostic version, see `principal-production-engineer/reference/memory_data_ownership.md`.

## Doctrine

> Shape the data like the access pattern. Keep structures plain. Make the control flow flat enough that the compiler — and the CPU — can predict what comes next.

Three levers, in priority order:

1. **Dense, contiguous data** → cache and prefetcher work for you.
2. **Plain structures + free functions** → fewer abstractions to penetrate; the compiler sees through to the operations.
3. **Straightforward control flow** → branch predictor, vectorizer, and inliner all do their best work on flat, regular code.

## Choose the layout from the access pattern

Decide AoS vs SoA from what the hot loop actually touches.

```cpp
// AoS: natural when most fields are touched together per element.
struct Particle { float x, y, z, vx, vy, vz; float mass; uint32_t flags; };
std::vector<Particle> particles;

// SoA: better when hot loops touch one field across many records.
struct Particles {
    std::vector<float> x, y, z;
    std::vector<float> vx, vy, vz;
    std::vector<float> mass;
    std::vector<uint32_t> flags;
};
```

A pure-position integration step (`x += vx * dt`) over `Particles` SoA streams two arrays, hits L1d almost perfectly, and vectorizes cleanly. The same step over `Particle` AoS loads `mass` and `flags` for every element and wastes bandwidth.

When in doubt, write both and benchmark — but default to SoA whenever a hot loop touches a *subset* of fields.

## Dense container choices

| Use | Avoid in hot paths |
|---|---|
| `std::vector<T>`, `std::array<T, N>`, `std::span<T>` | `std::list<T>`, `std::forward_list<T>` |
| Open-addressed hash tables: `absl::flat_hash_map`, `ankerl::unordered_dense` | `std::map`, `std::unordered_map` (node-based; pointer chasing) |
| `std::flat_map` / `std::flat_set` (C++23) for small associative containers | `std::set` |
| `boost::small_vector`, `absl::InlinedVector` (inline storage avoids heap for short data) | `std::deque` when contiguity matters |
| `std::pmr::vector` + monotonic / pool resources for phase-scoped allocation | Per-element `new` / `make_shared` |
| `std::bitset`, `std::vector<bool>` (compact but with caveats), or a `Bits` wrapper | Boolean flags as one `bool` per byte when memory is tight |

The default container for ordered hot-path data is `std::vector<T>` with `reserve()` called once.

## Indices over pointers

Replace pointer graphs with index-based handles. Indices:

- preserve density when the backing storage moves;
- are stable across `vector` reallocation;
- are smaller (often 4 bytes vs 8) and cache-friendlier;
- serialize trivially.

```cpp
using EntityId = uint32_t;

struct World {
    std::vector<Position> positions;     // parallel arrays: index == EntityId
    std::vector<Velocity> velocities;
    std::vector<Health>   healths;
};
```

### Generational handles

Plain indices invalidate when slots are reused. A `(slot, generation)` handle catches use-after-free:

```cpp
struct Handle { uint32_t slot; uint32_t generation; };

template <typename T>
class SlotMap {
    struct Slot { T value; uint32_t generation; bool occupied; };
    std::vector<Slot>     slots;
    std::vector<uint32_t> free_list;

public:
    [[nodiscard]] Handle insert(T value);
    [[nodiscard]] T*     get(Handle h) noexcept;       // returns nullptr if generation mismatches
    [[nodiscard]] bool   erase(Handle h) noexcept;
};
```

This is the workhorse for ECS, graphics object pools, and any system that must hand out stable references into a moving array.

### Pool / arena allocation

Use pools when you allocate and free many same-sized objects with phase-based lifetimes:

```cpp
class FramePool {
    std::pmr::monotonic_buffer_resource arena;
public:
    explicit FramePool(std::size_t bytes) : arena(bytes) {}
    std::pmr::polymorphic_allocator<std::byte> allocator() { return {&arena}; }
    void reset() noexcept { arena.release(); }    // single bulk free at frame end
};
```

See [`cpp_ownership_and_arenas.md`](cpp_ownership_and_arenas.md) for arena lifetime rules.

## Simplicity: structures over hierarchies

- **Plain `struct` with public fields** when there is no invariant to enforce. Encapsulation has a cost; pay it only when there's something to protect.
- **Free functions** for operations that don't need privileged access. They compose better, test better, and inline more aggressively.
- **No inheritance for code reuse** — inheritance is for substitutability. Use composition (and free functions) for reuse.
- **Closed-set polymorphism → `std::variant` + `std::visit`** instead of `virtual`. No vptr, no indirection; the compiler often lowers `visit` to a jump table or even direct dispatch.
- **CRTP** when the set is known at compile time and you need static polymorphism with full inlining.

```cpp
// Polymorphic shape with virtual dispatch.  Vptr per instance; no inlining.
struct Shape { virtual float area() const = 0; virtual ~Shape() = default; };

// Closed-set with variant — flat, no vptr, dispatch resolves to a switch.
struct Circle    { float r; };
struct Rectangle { float w, h; };
using AnyShape = std::variant<Circle, Rectangle>;

float area(AnyShape const& s) noexcept {
    return std::visit([](auto const& v) -> float {
        if constexpr (std::is_same_v<std::decay_t<decltype(v)>, Circle>)
            return 3.14159f * v.r * v.r;
        else
            return v.w * v.h;
    }, s);
}
```

See [`vtables_and_polymorphism.md`](vtables_and_polymorphism.md) for the full dispatch-cost analysis.

## Control flow the compiler can optimize

Vectorizer, branch predictor, and inliner all prefer flat, regular, no-aliasing loops.

### Prefer

- Guard clauses up front; flat nesting (≤ 2 levels) in hot loops.
- **Stride-1 access** over contiguous data.
- **No per-element function calls** to opaque code in the inner loop.
- **No early exits / `break`** in the hot loop when vectorization matters — split the loop instead.
- **No aliasing** — annotate `const T* __restrict__ in, T* __restrict__ out` when supported (GCC/Clang); pass non-overlapping `std::span<const T>` and `std::span<T>` to communicate the same to the compiler conceptually.
- **Branch-free idioms** for tight conditionals:
  ```cpp
  // Branch: predictor-dependent on data
  for (int x : data) total += (x > 0) ? x : 0;

  // Branch-free: compiles to cmov / select
  for (int x : data) total += std::max(x, 0);
  ```
- **Sort data before branching on it** when the conditional is data-dependent — predictor accuracy dominates.
- **Lookup tables** instead of cascaded `if` chains for small, fixed mappings.
- **Range-`for` over contiguous containers** so the compiler can fuse/vectorize.

### Avoid

- `std::function` and capturing lambdas in inner loops — opaque indirect calls block inlining.
- Virtual calls in inner loops — same problem, plus the vptr load. See [`vtables_and_polymorphism.md`](vtables_and_polymorphism.md).
- Deep `if` / `switch` nests where each branch does different work — split into separate passes.
- Exceptions for control flow on the hot path — even when not thrown, they constrain optimization.
- `std::shared_ptr` per element — atomic refcount per access. See [`cpp_ownership_and_arenas.md`](cpp_ownership_and_arenas.md).

## Vectorization checklist

For a loop to vectorize automatically (GCC `-O3` / Clang `-O3` / MSVC `/O2`):

1. Contiguous data (`std::vector`, `std::array`, `std::span`).
2. Known or computable iteration count at loop entry.
3. No data dependencies across iterations (no read of a write made by an earlier iteration).
4. No aliasing between inputs and outputs.
5. No exceptions, no function calls to opaque code, no virtual dispatch.
6. Aligned data when SIMD lane width matters (`alignas(32)` for AVX2, `alignas(64)` for AVX-512).

When the auto-vectorizer can't, reach for explicit SIMD: `std::experimental::simd` (C++ TS), `xsimd`, Google `highway`, or hand-written intrinsics. Always benchmark before and after.

## Hot / cold split

Split fields by access frequency. Cold data in a side table, indexed by handle.

```cpp
// Before: every Entity carries diagnostic strings, padding the cache line.
struct Entity {
    EntityId id;
    Position pos;          // hot
    Velocity vel;          // hot
    std::string name;      // cold
    std::string asset_path; // cold
    DebugInfo debug;       // cold
};

// After: hot table is dense and small; cold data is looked up only when needed.
struct EntityHot {
    EntityId id;
    Position pos;
    Velocity vel;
};

struct EntityCold {
    std::string name;
    std::string asset_path;
    DebugInfo   debug;
};

std::vector<EntityHot>                       hot;     // streamed every frame
absl::flat_hash_map<EntityId, EntityCold>    cold;    // touched only on lookup
```

Hot path now streams ~24 bytes per entity instead of ~120; 2–3× more fit per cache line. See [`cache_lines_and_alignment.md`](cache_lines_and_alignment.md) for the underlying mechanism.

## Common patterns

### Column-oriented Entity-Component-System

Each component is a column; entities are indices. Systems iterate columns directly — pure SoA over the components a system actually needs.

```cpp
struct PhysicsSystem {
    std::span<const Position> in_pos;
    std::span<const Velocity> in_vel;
    std::span<Position>       out_pos;

    void step(float dt) noexcept {
        for (std::size_t i = 0; i < in_pos.size(); ++i) {
            out_pos[i].x = in_pos[i].x + in_vel[i].x * dt;
            out_pos[i].y = in_pos[i].y + in_vel[i].y * dt;
            out_pos[i].z = in_pos[i].z + in_vel[i].z * dt;
        }
    }
};
```

Each line vectorizes; no virtual calls; the entire data set streams from L1.

### Bit-packed flags

```cpp
struct Flags { std::uint32_t bits; };
constexpr std::uint32_t kActive  = 1u << 0;
constexpr std::uint32_t kVisible = 1u << 1;
constexpr std::uint32_t kFrozen  = 1u << 2;
// 32 booleans in 4 bytes; one cache line holds 16 entities worth.
```

### Tagged-union dispatch

Closed enum + jump table beats `virtual` for small, stable hierarchies:

```cpp
enum class Op : std::uint8_t { Add, Sub, Mul, Div };

float apply(Op op, float a, float b) noexcept {
    switch (op) {
        case Op::Add: return a + b;
        case Op::Sub: return a - b;
        case Op::Mul: return a * b;
        case Op::Div: return a / b;
    }
    __builtin_unreachable();   // helps codegen drop the safety branch
}
```

## Anti-patterns

- `std::vector<std::unique_ptr<Base>>` iterated polymorphically in a hot loop — heap fragmentation + vptr load + missed inlining per element.
- `std::list<T>` used "for fast inserts" without measuring — almost always loses to `std::vector` + `erase`/`insert` for any realistic size.
- `std::unordered_map<std::string, T>` on a hot path — string hashing, separate chaining, per-bucket allocation. Replace with `absl::flat_hash_map` and an interned/integer key.
- Deep object trees with bidirectional parent/child pointers, traversed every frame.
- `std::function<void()>` queues processed in inner loops.
- `for (auto x : container)` where `x` is a heavy type that should be `auto const&`.
- Premature `template`-ization of code that has one caller and one type.

## Verification

Make the optimizer prove you right. Never claim a layout is faster without:

- **Microbenchmark** — Google Benchmark (`benchmark::DoNotOptimize`, `benchmark::ClobberMemory`). Compare before and after on representative data sizes.
- **Vectorization reports** — `gcc -O3 -fopt-info-vec-all`, `clang -O3 -Rpass=loop-vectorize -Rpass-missed=loop-vectorize`. Confirms whether the auto-vectorizer fired.
- **Generated assembly** — Compiler Explorer (`godbolt.org`) or `objdump -d -C binary | less`. Verify the inner loop is tight and the expected instructions emit.
- **Cache and IPC** — `perf stat -e cycles,instructions,L1-dcache-loads,L1-dcache-load-misses,LLC-load-misses ./bin`. Watch IPC and miss rates trend the right way.
- **Cache-line contention** — `perf c2c` (Linux) for false-sharing events.
- **Memory footprint** — `valgrind --tool=massif` or `heaptrack` to validate that "denser" is actually denser in practice (allocator overhead can surprise).
- **Bench against the dumb version** — always keep a simple `std::vector` baseline. If the clever SoA / ECS / arena layout isn't measurably faster on the workload you care about, it isn't earning its complexity.

Performance claims without measurement are folklore. The `principal-production-engineer` skill's verification discipline applies in full.
