# Imports and Redundancy

Covers keeping imports unconditional and top-level, and removing duplicated logic / data / validation. Load this when you see `try`/`except ImportError`, imports buried inside functions, copy-pasted branches, or the same check repeated across call sites.

## Doctrine

> A dependency is either required or it isn't. An optional import is a hidden runtime branch that turns "missing package" into "mysterious behavior change three functions away."

> Every fact should have one home. Duplicated logic drifts; duplicated validation hides which copy is the real gate.

## Optional imports — almost always wrong

```python
try:
    import ujson as json          # silently different behavior, different bugs
except ImportError:
    import json
```

Problems: two code paths to test, divergent edge cases, a typo'd extra that "works" with degraded behavior nobody notices, type checkers seeing one branch.

**Instead:**
- The dependency is **required** → declare it in `pyproject.toml` and `import` it at top level, unconditionally. Let `ImportError` be loud at startup if the environment is broken.
- The dependency is a **genuine optional feature** (plugin, accelerator) → make it an extra (`pkg[fast]`), and at the *use site* fail with a clear, actionable error:

```python
def to_arrow(df):
    try:
        import pyarrow
    except ImportError as e:
        raise RuntimeError("Arrow export needs the 'fast' extra: pip install pkg[fast]") from e
    ...
```

The difference: the legitimate case **raises with instructions**, it does not silently substitute a fallback implementation.

## Imports go at the top, unconditionally

| Pattern | Verdict |
|---|---|
| Module-level `import x` | Default. Always. |
| Import inside a function | Only to break a real circular import, or to defer a genuinely heavy/optional import — and comment why. |
| `import *` | Never in library code — pollutes namespace, breaks tooling, hides origins. |
| Conditional import for platform (`if sys.platform == "win32": import winreg`) | OK — that's real environment branching, not optionality. Keep it at module top. |

Function-local imports as a habit (rather than for cycles/cost) hide dependencies and pay the import-lookup cost on every call.

## Redundancy — collapse it to one home

- **Duplicated logic** → extract a function. The rule of three is a ceiling, not a license: two copies that will obviously diverge should be unified now.
- **Repeated validation** → validate once at the boundary; don't re-check inward (see [fail_fast.md](fail_fast.md)). Re-validation signals you don't trust the boundary — fix the trust, not by adding checks.
- **Duplicated constants / config** → one definition, imported. Two copies *will* drift.
- **Parallel data kept in sync by hand** (two dicts, an enum + a string list) → derive one from the other; see [enums_over_strings.md](enums_over_strings.md).
- **Copy-pasted branches** that differ only in a value → table-driven dispatch; see [control_flow.md](control_flow.md).
- **Redundant computation** in a loop → hoist the invariant part out.

**But:** don't over-DRY. Two pieces of code that *look* alike but answer to different requirements should stay separate — coupling them so one change breaks two unrelated callers is worse than duplication. DRY is about single source of truth for *one fact*, not deduplicating coincidental similarity.

## Anti-patterns

- `try/except ImportError` that swaps in a fallback implementation silently.
- Importing inside a function "to speed up startup" without measuring that startup is actually slow.
- A `utils.py` constant copied into a test/another module instead of imported.
- The same `if not x: raise` repeated in five callers of one function — push it into the function.
- Wrapper functions that only re-export another function unchanged.
- Defaulting a missing optional dep to a no-op so the feature silently does nothing.

## Code-review checklist

- [ ] No `try/except ImportError` fallback; optional deps are extras that raise an actionable error at use.
- [ ] Imports are top-level and unconditional except for documented cycle/cost/platform cases.
- [ ] No `import *` in library code.
- [ ] Required dependencies are declared in `pyproject.toml`.
- [ ] No constant/logic/validation duplicated across modules that could drift.
- [ ] Deduplication unifies a single fact, not coincidentally-similar code with different reasons to change.

## Verification commands

```bash
ruff check --select PLC0415 .   # import-outside-top-level
ruff check --select F403,F405 . # import * and names possibly from a star import
ruff check --select TID .       # flake8-tidy-imports: banned/relative-import policy
pylint --disable=all --enable=duplicate-code path/   # R0801: duplicated blocks across files
deptry .                        # missing (undeclared) and unused/obsolete dependencies
```

`deptry` catches the real risk behind optional imports — a dependency used but not declared. `R0801` surfaces copy-paste redundancy across files.
