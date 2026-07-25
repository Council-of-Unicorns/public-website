# Abstractions — ABCs, Protocols, and When Not to Abstract

Covers choosing the right abstraction mechanism in Python — abstract base classes, `typing.Protocol`, plain functions, dataclasses — and resisting abstraction you don't yet need. Load this when introducing a base class / interface, deciding inheritance vs composition, or reviewing a class hierarchy.

## Doctrine

> Abstract to remove duplication that already exists or to name a contract with ≥2 real implementations. Never abstract for a future that hasn't arrived.

The cost of a wrong abstraction is higher than the cost of duplication: duplication is local and deletable; a wrong abstraction couples everything that depends on it. Prefer the concrete until a second real case forces the shape.

## Decision table — which mechanism

| You need… | Use | Why |
|---|---|---|
| Behavior with **no shared state**, one implementation | a **function** | A class with one method and no state is a function. |
| A **contract** satisfied by types you don't own / can't subclass | **`typing.Protocol`** | Structural typing — duck typing the checker enforces; no inheritance required. |
| A contract **+ shared implementation** across ≥2 of *your* classes | **ABC** (`abc.ABC` + `@abstractmethod`) | Forces subclasses to implement, can carry concrete helper methods. |
| A bag of typed data | **`@dataclass`** (`frozen=True`, `slots=True`) | Don't write a class hierarchy for data. |
| A fixed set of named choices | **`Enum`** | See [enums_over_strings.md](enums_over_strings.md), not a class per choice. |
| Vary behavior by passing in a strategy | **composition** (pass a callable / object) | Inject the behavior; don't subclass to change it. |

## Protocol vs ABC — the key distinction

```python
# Protocol: structural. Any object with these methods qualifies — no base class, no import coupling.
from typing import Protocol

class Reader(Protocol):
    def read(self, n: int) -> bytes: ...

def consume(r: Reader) -> bytes:    # accepts files, sockets, BytesIO, your class — all without inheriting
    return r.read(1024)
```

```python
# ABC: nominal. Subclasses must explicitly inherit and implement; can share concrete code.
from abc import ABC, abstractmethod

class Exporter(ABC):
    @abstractmethod
    def write(self, rows: list[Row]) -> None: ...

    def export(self, rows: list[Row]) -> None:   # shared template method
        self._validate(rows)
        self.write(rows)
```

**Choose `Protocol`** when you're defining what *callers require* of an argument (the interface belongs to the consumer, types may be third-party). **Choose `ABC`** when you own a family of classes that share real implementation and you want construction-time enforcement that abstract methods are filled in.

## Composition over inheritance

Inheritance is for **is-a + shared behavior**, not code reuse. If you're subclassing to borrow a method, you've coupled two classes' lifecycles to share a function — extract the function or inject a collaborator instead.

```python
# Avoid: inheriting to reuse
class CsvJob(BaseJob): ...          # only overrides one hook, inherits 8 methods it half-uses

# Prefer: compose the varying part
class Job:
    def __init__(self, writer: Writer) -> None:   # Writer is a Protocol
        self._writer = writer
```

Reserve `@abstractmethod` for the genuinely-required hooks; everything concrete stays concrete.

## Prefer / avoid

**Prefer**
- One concrete class until a second implementation actually exists; introduce the ABC/Protocol *at that moment*.
- `Protocol` for boundaries with external/std-lib types.
- `@dataclass(frozen=True, slots=True)` for data; `Enum` for closed choices.
- Composition + dependency injection of small collaborators.
- Abstract base methods that are *all* abstract or backed by a real template method.

**Avoid**
- `BaseManager` / `AbstractServiceFactory` with one subclass — speculative; delete the base, keep the class.
- Deep hierarchies (≥3 levels) — flatten; prefer composition.
- Mixins that reach into `self` attributes they don't define — fragile coupling.
- ABCs that exist only to "enforce an interface" with zero shared code — that's a `Protocol`.
- Inheriting from a concrete class to tweak one method (call super everywhere, override one) — compose.
- Abstract methods with default `pass` bodies — that's not abstract; it's an optional hook pretending to be a contract.

## Anti-patterns

- **Premature framework.** A plugin registry / factory / base class before there are two plugins.
- **Inheritance for reuse.** `class Foo(Helpers)` to get utility methods — make them free functions.
- **God ABC.** A base class accreting every method any subclass might want; subclasses raise `NotImplementedError` for the ones they don't.
- **Protocol where a function suffices.** A one-method `Protocol` passed once is just a `Callable[...]` type hint.

## Code-review checklist

- [ ] Every ABC/base class has ≥2 real subclasses (or one with a concrete second imminent and named).
- [ ] Interfaces over external/std-lib types are `Protocol`, not ABCs that can't be inherited.
- [ ] No inheritance used purely for code reuse — that's composition.
- [ ] No `@abstractmethod` with a `pass`/default body masquerading as a contract.
- [ ] Data is a `@dataclass`/`Enum`, not a hand-rolled class hierarchy.
- [ ] Hierarchies are ≤2 levels deep; deeper ones justified or flattened.
- [ ] Single-method `Protocol`/class that's really a `Callable` is simplified.

## Verification commands

```bash
mypy --strict path/    # @abstractmethod not implemented → error; Protocol conformance checked structurally
pyright path/           # same, with explicit "X is not abstract / missing member" diagnostics
ruff check --select B024 .   # abstract base class with no abstract methods (likely should be Protocol/concrete)
ruff check --select B027 .   # empty method in ABC without @abstractmethod (the "pass-body hook" smell)
pylint --enable=R0901,R0902 path/   # too-many-ancestors / too-many-instance-attributes (over-deep hierarchies)
```

`mypy`/`pyright` are what make abstractions *real*: an unimplemented `@abstractmethod` or a type that fails to satisfy a `Protocol` is a type error, not a runtime surprise. `B024`/`B027` catch ABCs that should have been Protocols or concrete classes.
