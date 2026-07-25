# Control Flow — Reduce Logical Branches

Covers how to keep Python control flow flat and few-branched: guard clauses, early returns, and replacing `if`/`elif` chains with data-driven dispatch. Load this when writing or reviewing code whose nesting depth, branch count, or duplicated conditionals are getting hard to follow.

## Doctrine

> Every branch is a place a bug can hide and a path a test must cover. Fewer, flatter branches = fewer untested states.

- Prefer **early return / guard clauses** to nested `if`.
- Prefer **data-driven dispatch** (dict, enum→handler) to long `if`/`elif`/`else` ladders.
- Prefer **polymorphism** to `isinstance` ladders when the set of types is open.
- Branch on **one axis at a time**; never on a boolean parameter that splits a function into two unrelated behaviors.

## When to flatten vs leave alone

| Situation | Action |
|---|---|
| `if` nested ≥ 3 deep | Invert with guard clauses; return/`continue`/`raise` early. |
| `if/elif` ladder dispatching on a value | Replace with dict or `match`; see [enums_over_strings.md](enums_over_strings.md). |
| `isinstance` ladder over a closed type set | `match` with class patterns. |
| `isinstance` ladder over an open/extensible set | Polymorphism — a method on each type. |
| Two-deep `if` reading naturally top-to-bottom | Leave it. Flattening can hurt clarity. |

## Prefer / avoid

**Prefer**
```python
def charge(order: Order) -> Receipt:
    if order.is_empty():
        raise EmptyOrderError(order.id)
    if not order.customer.is_active:
        raise InactiveCustomerError(order.customer.id)
    if order.total <= 0:
        raise InvalidTotalError(order.total)
    return _settle(order)
```

**Avoid** — the arrow anti-pattern (deep nesting, the happy path buried at the bottom):
```python
def charge(order: Order) -> Receipt:
    if not order.is_empty():
        if order.customer.is_active:
            if order.total > 0:
                return _settle(order)
            else:
                raise InvalidTotalError(order.total)
        else:
            raise InactiveCustomerError(order.customer.id)
    else:
        raise EmptyOrderError(order.id)
```

## Dispatch tables over ladders

**Avoid**
```python
def area(shape):
    if shape.kind == "circle":
        return math.pi * shape.r ** 2
    elif shape.kind == "square":
        return shape.side ** 2
    elif shape.kind == "rect":
        return shape.w * shape.h
    else:
        raise ValueError(shape.kind)
```

**Prefer** — a table maps the discriminant to behavior; adding a case is one line, not a new branch:
```python
_AREA: dict[ShapeKind, Callable[[Shape], float]] = {
    ShapeKind.CIRCLE: lambda s: math.pi * s.r ** 2,
    ShapeKind.SQUARE: lambda s: s.side ** 2,
    ShapeKind.RECT:   lambda s: s.w * s.h,
}

def area(shape: Shape) -> float:
    return _AREA[shape.kind](shape)   # KeyError fails fast on an unhandled kind
```

When the discriminant is a closed enum, `match` gives the same flatness *plus* exhaustiveness checking from type checkers — see [enums_over_strings.md](enums_over_strings.md).

## Other branch-reducers

- **Boolean-parameter soup** → split into two functions. `render(fast=True)` that shares no code between branches is two functions wearing one name.
- **Repeated guard in every caller** → push the check into the callee once (single source of truth; see [imports_and_redundancy.md](imports_and_redundancy.md)).
- **`if x is None: x = default`** → use a real default or fail fast; don't paper over missing data (see [fail_fast.md](fail_fast.md)).
- **Flag accumulation** (`found = False; ... if found:`) → extract to a function and `return` directly, or use `any()`/`next()`/a comprehension.
- **Comprehensions** replace loop+append+filter, but stop at one `if` and one `for`; a comprehension with two conditions and a ternary is less readable than a loop.

## Anti-patterns

- Deeply nested `if`/`for`/`try` (the "arrow"). Invert and return early.
- `elif` ladders that grow with every new case — each addition is an edit to a hot function and a new untested path.
- Branching on `type(x) == SomeClass` — fragile to subclasses; use polymorphism or `match`.
- A single function with an `if mode == ...` at the top splitting it into disjoint behaviors — that's N functions.
- `else: pass` and `else: return None` that silently swallow the unhandled case — make the unhandled case raise.

## Code-review checklist

- [ ] No function nests control flow more than ~2 deep without a reason.
- [ ] `if`/`elif` ladders dispatching on a value are tables or `match`, not ladders.
- [ ] The happy path is at the top level, not the innermost block.
- [ ] No boolean parameter selects between two unrelated behaviors.
- [ ] Unhandled discriminant values fail loudly (`KeyError`, `raise`), not silently.
- [ ] Comprehensions stay simple; complex ones are loops.

## Verification commands

```bash
ruff check --select C901 .          # mccabe cyclomatic complexity (branch count) per function
ruff check --select SIM .           # flake8-simplify: collapsible ifs, needless else, ternaries
ruff check --select RET .           # flake8-return: unnecessary else after return, etc.
radon cc -s -n C .                  # rank functions by complexity; C or worse = too many branches
```

`C901` (set `--max-complexity`) is the direct signal: it counts branches. A function flagged here has too many paths — flatten or split it.
