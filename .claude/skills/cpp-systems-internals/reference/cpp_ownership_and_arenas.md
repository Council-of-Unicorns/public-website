# C++ Ownership, Smart Pointers, and Arenas

C++-specific ownership vocabulary, lifetime rules, and arena patterns. For language-agnostic data-layout and ownership principles, see `principal-production-engineer/reference/memory_data_ownership.md`.

## Ownership vocabulary

Use types as ownership documentation.

| Type | Meaning |
|---|---|
| `T` (value) | Owned directly |
| `T&` | Required non-owning borrow |
| `T*` | Optional non-owning borrow; may be null |
| `std::span<T>` | Borrowed contiguous range |
| `std::unique_ptr<T>` | Unique ownership; ownership transfer via move |
| `std::shared_ptr<T>` | True shared lifetime only |
| `std::weak_ptr<T>` | Observer for shared ownership; cycle-breaker |
| arena pointer/view | Valid only for the arena's lifetime phase |

Do not reach for `shared_ptr` because ownership is unclear — clarify ownership instead.

## Smart pointer policy

### `std::unique_ptr<T>`
One owner; movable ownership transfer. Use for factories, polymorphic owned objects, and dynamic resources.

### `std::shared_ptr<T>`
Use *only* when shared lifetime is real and unavoidable. It carries cognitive load, atomic refcount cost, cycle-leak risk, and lifetime-debugging difficulty. Not a default.

### `std::weak_ptr<T>`
Use only to observe already-justified shared ownership or to break cycles.

### Raw pointer
Optional non-owning borrow. Names should imply lookup/optional behavior (e.g., `find_session`).

### Reference
Required non-owning borrow.

## Memory safety rules

- No raw owning pointers.
- No dangling views/spans.
- No unchecked buffer writes.
- No `reinterpret_cast` over wire data unless alignment, endianness, size, and lifetime are proven.
- No lifetime hidden behind callbacks.
- No storing references into resizable containers unless stability is guaranteed.
- No shared mutable ownership without synchronization.
- No hidden ownership through global registries or service locators.
- No use-after-reset arena references.
- No fallible allocation hidden in a hard real-time / hot path.

## Arenas

Use arenas when lifetimes are phase-based:

- per request
- per tick / frame
- per packet batch
- per simulation step
- per compiler pass
- per training batch

### Good API shape

```cpp
[[nodiscard]] ParseResult parse(ByteSpan input, Arena& scratch) noexcept;
```

### Rules

- Arena lifetime must be explicit.
- Arena-allocated objects must not escape the arena's phase.
- Do not mix arena ownership with shared ownership.
- Do not rely on destructors unless the arena supports them.
- Arena reset must happen at a clear phase boundary.
- Tests should cover escape hazards.

## C++17 / 20 / 23 additions

- `std::pmr` — polymorphic allocators; swap arena strategies without templating the container on the allocator type.
- `std::expected<T, E>` (C++23) — non-throwing failure return type; combine with `[[nodiscard]]`.
- `std::ranges::subrange` — typed borrowed range, similar to `span`.
- `std::out_ptr` / `std::inout_ptr` (C++23) — safer interop with C APIs returning pointers via out-parameters.

## Verification

- **AddressSanitizer** (`-fsanitize=address`) — use-after-free, heap/stack out-of-bounds, dangling stack.
- **UBSan** (`-fsanitize=undefined`) — alignment violations, signed overflow, invalid enum/bool values.
- **ThreadSanitizer** (`-fsanitize=thread`) — data races, lock-order inversions.
- **valgrind --tool=memcheck** — leak detection in older toolchains.
- **clang-tidy** checks — `clang-analyzer-core.*`, `cppcoreguidelines-owning-memory`, `bugprone-use-after-move`.
- **Static analyzers** — Clang Static Analyzer, MSVC `/analyze`, PVS-Studio, Coverity.

## Review questions

- Is ownership visible at every API boundary?
- Can any view/span/reference outlive its source?
- Is every `shared_ptr` justified by real shared lifetime?
- Are temporary allocations confined to an arena phase, with no escapes?
- Does any hot path allocate, throw, block, log, or call a virtual function unexpectedly?
- Are smart pointers used for ownership, never as ambiguity?
