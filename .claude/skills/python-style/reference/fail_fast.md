# Fail Fast

Covers raising on bad state at the earliest point instead of masking it: boundary validation, narrow `except`, no silent fallbacks, no defensive defaults that hide missing data. Load this when reviewing error handling, `try`/`except` blocks, `.get(...)` defaults, or `or`-defaulting on possibly-missing values.

## Doctrine

> A program that crashes at the cause is debuggable. A program that limps on with corrupted state fails later, somewhere else, for reasons no traceback explains.

- **Validate at the boundary**, once, then trust the value inward.
- **Raise immediately** on a broken invariant — don't return a sentinel and hope a caller checks it.
- **Catch narrowly** — only the exception you can actually handle, only around the line that raises it.
- **Never swallow** — no bare `except:`, no `except ...: pass`, no fallback that hides the failure.

## Boundary validation, then trust

```python
def load_config(path: Path) -> Config:
    if not path.is_file():
        raise FileNotFoundError(path)            # fail at the cause, with the cause
    raw = json.loads(path.read_text())           # JSONDecodeError propagates — good
    timeout = raw["timeout_s"]                   # KeyError naming the field — good
    if timeout <= 0:
        raise ValueError(f"timeout_s must be > 0, got {timeout}")
    return Config(timeout_s=timeout, ...)
```

Inside the system, downstream code receives a validated `Config` and does **not** re-check `timeout_s > 0` everywhere — that re-validation is redundancy (see [imports_and_redundancy.md](imports_and_redundancy.md)) and a sign the invariant isn't trusted. Validate once at the edge; let the type carry the guarantee.

## The failure taxonomy — what to do with each

| Failure kind | Response |
|---|---|
| Broken invariant / programmer error (impossible state, bad arg) | Raise immediately (`ValueError`, `AssertionError`, custom). Do not catch. |
| Semantic failure of the operation (parse failed, not found) | Raise a specific exception; let the caller decide. |
| Expected external failure (network, disk, 503) | Catch *that* exception narrowly; retry/degrade with an explicit budget; log + metric. |
| "Can't happen" branch | `raise AssertionError(...)` / `assert_never`, never `pass` or `return None`. |

## Prefer / avoid

**Avoid** — catch-all that turns every bug into a wrong answer:
```python
try:
    return compute(payload)
except Exception:
    return None            # KeyError? TypeError in compute? all silently → None
```

**Prefer** — narrow scope, narrow type, let the rest propagate:
```python
try:
    record = self._cache[key]
except KeyError:
    record = self._db.fetch(key)   # only the expected miss is handled
return compute(record)             # a bug in compute still raises
```

## Defensive defaults hide bugs

```python
name = data.get("name", "unknown")     # was 'name' supposed to be there? now you can't tell
qty  = payload.get("qty") or 1         # qty == 0 silently becomes 1 (falsy-trap)
```

If the key is required, index it (`data["name"]`) so its absence raises at the source. Use a default only when "missing" is a real, valid, documented state — not to keep the program from crashing. Beware `or`-defaults on values where `0`/`""`/`[]`/`False` are legitimate; use an explicit `is None` check.

## assert vs raise

- `assert` documents an **internal invariant** the code believes is always true. It is stripped under `python -O`, so never use it for input validation or anything security-relevant.
- `raise` validates **external input** and enforces contracts that must hold in production.

## Anti-patterns

- `except Exception: pass` / bare `except:` — the canonical bug-hider. If you truly must continue, log at minimum and comment *why*.
- Returning `None`/`-1`/`""` as an error signal that callers forget to check — raise instead, or return an explicit `Result`/`Optional` the type checker forces them to unwrap.
- Broad `try` wrapping 40 lines — you can't tell which line the caught exception came from. Wrap the single risky call.
- `except` that catches, logs, and re-raises a *different* generic exception, dropping the original — use `raise NewError(...) from err`.
- Retrying without a bounded budget — unbounded retries are a silent fallback that hangs instead of failing.
- "Defensive" `if obj is not None:` guards everywhere because some upstream function *might* return `None` — fix the upstream to not return `None`, or make it raise.

## Code-review checklist

- [ ] Inputs validated once at the boundary; interior code trusts validated values.
- [ ] No bare `except:` / `except Exception: pass`; every `except` names a specific type.
- [ ] `try` blocks wrap the minimum risky lines, not whole function bodies.
- [ ] No error signaled by a sentinel return that a caller can silently ignore.
- [ ] `.get(k, default)` / `x or default` used only where missing/falsy is genuinely valid.
- [ ] Re-raises preserve the cause (`raise ... from err`).
- [ ] Retries/fallbacks for external failures have an explicit bound and emit a log/metric.
- [ ] `assert` used only for internal invariants, never input validation.

## Verification commands

```bash
ruff check --select BLE .    # flake8-blind-except: bare/broad except
ruff check --select B .      # flake8-bugbear: B012 (except/pass), B904 (raise without from), more
ruff check --select TRY .    # tryceratops: try/except anti-patterns, broad raises
ruff check --select SIM105 . # suppressible exception → use contextlib.suppress explicitly
mypy --strict path/          # forces Optional unwrapping; flags ignored error returns
```

`BLE` + `B` + `TRY` together catch the bulk of swallowed-exception and silent-fallback patterns. Run them in CI so a new bare `except` fails the build.
