# C++ API Style: Explicit Failure, Ownership, and No Hidden Throwing

## Preferred systems API shape

For simple expected failure:

```cpp
[[nodiscard]] bool try_push(PacketView packet) noexcept;
[[nodiscard]] bool try_pop(Packet& out) noexcept;
[[nodiscard]] bool contains(Key key) const noexcept;
[[nodiscard]] bool reserve_exact(size_t count) noexcept;
```

For failure where the reason matters:

```cpp
[[nodiscard]] Result<Frame, ParseError> parse_frame(ByteSpan input) noexcept;
[[nodiscard]] Result<void, SendError> send(PacketView packet) noexcept;
[[nodiscard]] Result<Config, ConfigError> load_config(PathView path);
```

For required borrow:

```cpp
void process(Session& session) noexcept;
```

For optional borrow:

```cpp
[[nodiscard]] Session* find_session(SessionId id) noexcept;
```

For ownership transfer:

```cpp
[[nodiscard]] std::unique_ptr<Transport> make_transport(Config cfg);
```

## Why `[[nodiscard]] bool noexcept`

This communicates:

- operation may fail normally;
- caller must check result;
- function will not throw;
- control flow is local;
- ABI and performance model are simple;
- failure is expected, not exceptional.

Use it only when yes/no is sufficient. If the caller needs the reason, return `Result<T, E>` or `Status`.

## Naming conventions

- `try_foo`: expected failure returns `false`/error, no throwing.
- `find_foo`: optional non-owning borrow, may return null.
- `get_foo`: required, should not return null.
- `make_foo`: creates and returns ownership.
- `fetch_foo`: may perform I/O; name should reveal potential blocking.
- `parse_foo`: validates input and returns explicit result.

## Avoid exception smuggling

If an API is `noexcept`, do not call untrusted throwing callbacks inside it unless contained and converted to explicit failure at a boundary.

Bad:

```cpp
[[nodiscard]] bool process(PacketView p) noexcept {
    callback_(p); // may throw
    return true;
}
```

Better:

```cpp
[[nodiscard]] Result<void, ProcessError> process(PacketView p) noexcept;
```

or make the callback contract non-throwing.

## Avoid ambiguous APIs

Bad:

```cpp
Foo* get_foo();
Packet pop();
void push(Packet p);
void send(Packet p, bool reliable, bool flush);
```

Better:

```cpp
Foo& get_foo() noexcept;
Foo* find_foo(Id id) noexcept;
[[nodiscard]] bool try_pop(Packet& out) noexcept;
[[nodiscard]] bool try_push(PacketView p) noexcept;
send(PacketView p, SendOptions opts) noexcept;
```

## Invariants in types

Prefer:

```cpp
enum class ConnState { Opening, Open, Draining, Closed };
struct NonZeroU32 { uint32_t value; };
struct ValidPacket { Header header; ByteSpan payload; };
```

Over raw booleans and primitive obsession.

## Compiler hints

Use `[[likely]]` / `[[unlikely]]` sparingly and only for well-known, measured, or obvious paths such as malformed input or fatal errors. Data layout and algorithmic changes usually matter more.

## Production API checklist

- Does the name reveal blocking/allocation/I/O if present?
- Are all failures visible?
- Are return values `[[nodiscard]]` when ignoring them is a bug?
- Is ownership visible?
- Is throwing behavior clear?
- Can a caller misuse this API silently?
- Is the hot-path performance model obvious?
- Are default/fallback behaviors explicit and observable?
