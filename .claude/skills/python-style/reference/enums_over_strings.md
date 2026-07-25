# Enums Over Magic Strings

Covers replacing string (and int) literals used as discriminants with `Enum`/`StrEnum`, and the `if x == "..."` ladders that follow them with `match` or dict dispatch. Load this when you see string constants compared in conditionals, passed as "mode"/"type"/"status" parameters, or used as dict keys for behavior.

## Doctrine

> A string used as a discriminant is an untyped enum with no autocomplete, no exhaustiveness check, and a typo waiting to become a silent bug.

Replace magic-string discriminants with an enum when the value:
- is compared in more than one place, **or**
- selects behavior (`if status == "active"`), **or**
- is a fixed, known set (states, kinds, modes, roles).

Leave strings as strings when they are **opaque data** (names, IDs, free text, external keys you don't branch on).

## Which enum class

| Use | When |
|---|---|
| `enum.Enum` | Default. Members are distinct, identity-compared, not interchangeable with their values. |
| `enum.StrEnum` (3.11+) | The value must also *be* a str for serialization / JSON / DB columns — `Status.ACTIVE == "active"` and it serializes as `"active"`. |
| `enum.IntEnum` | Interop with C/protocols/bitfields where the member must behave as an int. |
| `enum.Flag` / `IntFlag` | Combinable bit flags (`Perm.READ | Perm.WRITE`). |
| `typing.Literal["a", "b"]` | A tiny closed set at an API boundary where defining a class is overkill *and* the type checker enforces membership. Promote to an enum once it's used for dispatch. |

## Prefer / avoid

**Avoid** — magic strings + comparison ladder:
```python
def transition(order, status):
    if status == "pending":
        ...
    elif status == "shipped":
        ...
    elif status == "delivrd":      # typo: silently never matches, no error
        ...
```

**Prefer** — enum + `match`; the type checker flags an unhandled member and a typo is an `AttributeError` at import:
```python
class Status(StrEnum):
    PENDING = "pending"
    SHIPPED = "shipped"
    DELIVERED = "delivered"

def transition(order: Order, status: Status) -> None:
    match status:
        case Status.PENDING:   ...
        case Status.SHIPPED:   ...
        case Status.DELIVERED: ...
```

## Exhaustiveness — make "forgot a case" a type error

Add an `assert_never` default. When a new member is added and a `match`/dispatch misses it, `mypy`/`pyright` flag the call site at type-check time; if it slips through, it raises at runtime instead of silently falling through.

```python
from typing import assert_never

def label(status: Status) -> str:
    match status:
        case Status.PENDING:   return "Waiting"
        case Status.SHIPPED:   return "On the way"
        case Status.DELIVERED: return "Done"
        case _ as unreachable:
            assert_never(unreachable)   # type error if any member is unhandled
```

## Dict dispatch keyed by enum

For pure value→value or value→handler maps, a dict beats both ladder and `match`:
```python
_RETRYABLE: dict[Status, bool] = {
    Status.PENDING: True,
    Status.SHIPPED: False,
    Status.DELIVERED: False,
}
# Guard completeness once, at import, so a missing member fails fast:
assert _RETRYABLE.keys() == set(Status)
```

## Anti-patterns

- `if mode in ("a", "A", "auto"):` — normalize at the boundary into one enum member instead of accepting variants everywhere.
- Enum whose members are only ever used as `.value` strings — then it's not buying you anything; either branch on the member or keep a plain constant.
- Parallel enums kept in sync by hand (one for the DB string, one for the code) — use `StrEnum` so there's one definition.
- Stringly-typed dict keys for dispatch (`handlers["shipped"]`) — key by the enum member.
- Comparing `status.value == "shipped"` — compare the member (`status is Status.SHIPPED`); reaching for `.value` in a branch is a smell.

## Code-review checklist

- [ ] No string/int literal is compared in a conditional to decide behavior.
- [ ] Fixed sets of modes/states/kinds/roles are enums, not strings.
- [ ] `match`/dispatch over an enum has an `assert_never` (or completeness assert for dicts).
- [ ] `StrEnum`/`IntEnum` used only where the value must interoperate as str/int; otherwise plain `Enum`.
- [ ] No hand-synced parallel enums or duplicated literal sets.

## Verification commands

```bash
mypy --strict path/         # flags non-exhaustive match via assert_never; flags wrong-enum passed
pyright path/                # same exhaustiveness + literal-membership checking
ruff check --select PLR2004 .  # magic value used in comparison (pylint rule) — candidates for an enum/const
grep -rnE '== *"[a-z_]+"' --include='*.py' src/   # quick scan for stringly-typed branches
```

`assert_never` is the linchpin: without a `mypy`/`pyright` run it does nothing for you at authoring time. Wire the type checker into CI so adding an enum member that isn't handled fails the build.
