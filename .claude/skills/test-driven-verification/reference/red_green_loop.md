# Red-Green Loop

Covers running red → green → refactor in practice and gating merges on it. Load this when implementing or hardening a change, reproducing a bug, or deciding what "done" means for a merge.

## Doctrine

> A test that is green before you wrote the code tests nothing. Watch it fail for the *right reason* first, or you are testing your test runner, not your code.

- **Red first.** Write the failing test, run it, read the failure. It must fail because the behavior is missing — not an import error, typo, or fixture bug.
- **Green minimal.** Write the *smallest* code that makes it pass. No speculative generality.
- **Refactor under green.** Improve names/structure only while the suite stays green; the tests are your safety net.
- **Every bug becomes a test.** Reproduce as a failing test *before* the fix. The test is both the proof and the permanent guard.
- **The gate is binary and stated up front.** "Looks done" is not a gate; `pytest -q` green + `mypy --strict` clean + ACs covered is.

### When to use / avoid

| Use | Avoid / adapt |
|---|---|
| Any nontrivial logic, bug fix, new AC | Throwaway spike (delete it after) |
| Boundaries you can assert on | Pure config/text with no behavior |
| Regression for a reported defect | Exploratory REPL work |

## The loop, concretely

A worked example: add `clamp(x, lo, hi)`.

**1. Red — write the test, watch it fail for the right reason.**
```python
# test_clamp.py
from mymod import clamp        # ImportError? that's the WRONG reason — stub first

def test_clamp_pulls_into_range():
    assert clamp(15, lo=0, hi=10) == 10
    assert clamp(-3, lo=0, hi=10) == 0
    assert clamp(5,  lo=0, hi=10) == 5
```
```bash
$ pytest -q test_clamp.py
E   assert 15 == 10        # RIGHT reason: behavior missing, not a typo
1 failed
```
Stub the symbol if the failure is an import/collection error, then re-run so the failure is the *assertion*.

**2. Green — smallest code that passes.**
```python
# mymod.py
def clamp(x: int, *, lo: int, hi: int) -> int:
    return max(lo, min(x, hi))
```
```bash
$ pytest -q test_clamp.py
1 passed
```

**3. Refactor — only while green.**
```bash
$ pytest -q            # full suite, still green → safe to rename/extract/inline
```
If a refactor reds the bar, revert the refactor — not the test.

## Regression from every bug

A bug means a missing test. Reproduce it *first* so you prove the test catches the defect on the **old** code.

```python
def test_clamp_rejects_inverted_bounds():   # bug: clamp(5, lo=10, hi=0) returned 0 silently
    with pytest.raises(ValueError):
        clamp(5, lo=10, hi=0)
```
```bash
$ git stash            # back to buggy code
$ pytest -q -k inverted_bounds
1 failed                # GOOD — the test actually reproduces the bug
$ git stash pop        # restore fix, re-run → passes
```
A regression test that passes on the unfixed code is guarding nothing.

## Binary merge gate

Define the gate before coding and make it mechanical. State it in the PR template:

```
Merge requires:
  [ ] pytest -q              green (0 failed, 0 error)
  [ ] mypy --strict          clean
  [ ] every new AC has a test referencing it
  [ ] evidence attached      (see evidence_capture.md)
  [ ] no @skip without a linked tracking issue
```

**Prefer / avoid**

- Avoid: "I tested it manually, looks done." — unrepeatable, no record, drifts on next change.
- Prefer: a stated gate run in CI that returns a single pass/fail and blocks merge mechanically.

## CI wiring

- Run the **same gate** on every push; do not let local and CI diverge.
- Mark the gate a **required status check** so the branch cannot merge red.
- **Fail fast** — order cheap checks first; stop the job on first failure of a stage.
- Keep the suite **fast enough to run locally** (seconds), so red is felt before push, not in CI.

```yaml
# .github/workflows/gate.yml
on: [push, pull_request]
jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -e ".[test]"
      - run: mypy --strict src/            # cheap, fail first
      - run: pytest -q --cov=src --cov-fail-under=85
```

## Flaky tests, handled honestly

A flake erodes trust in the whole gate. Treat it as a real defect.

1. **Detect** — re-run, and randomize order to surface hidden coupling:
   ```bash
   pytest -p randomly -q          # pytest-randomly: random order + seed each run
   pytest --count=20 -q test_x.py # pytest-repeat: shake out nondeterminism
   ```
2. **Quarantine visibly** — mark with a *reason and linked issue*, never a silent skip; log what is parked.
   ```python
   @pytest.mark.flaky_quarantine          # custom marker; CI reports the count
   @pytest.mark.skip(reason="flaky: order-dependent, tracking #482")
   def test_async_settles(): ...
   ```
3. **Fix the root cause** — almost always time, order, concurrency, or network. Inject the clock, isolate state, await deterministically, stub the boundary.

> Never mask a flake with blind unbounded retries — that hides nondeterminism instead of removing it, and converts a fast failure into a slow flaky pass.

## Anti-patterns

- Writing tests *after* the code, shaped to fit what the code already does (tests the implementation, not the spec).
- Weakening or deleting an assertion to "go green" — that is deleting the requirement.
- `@pytest.mark.skip` / `xfail` with no reason and no tracking issue.
- Retry-until-pass (`@flaky(max_runs=10)`) to paper over nondeterminism.
- Committing on red ("will fix in next commit") — breaks bisect and the gate.
- Green that came from an import/collection error you never read.

## Checklist (per change)

- [ ] Failing test written first and watched fail for the **right** reason.
- [ ] Minimal code to green; no speculative extras.
- [ ] Refactored only while the full suite was green.
- [ ] Each bug has a regression test that failed on the pre-fix code.
- [ ] Each new AC maps to a test (see [test_design.md](test_design.md)).
- [ ] `pytest -q` green and `mypy --strict` clean locally.
- [ ] No skips/xfails without a reason + tracking issue.
- [ ] Evidence captured (see [evidence_capture.md](evidence_capture.md)).
- [ ] Gate is a required CI status check.

## Verification

```bash
pytest -x --lf            # stop on first failure, run last-failed first — tightest red loop
pytest -p no:randomly     # force deterministic order to isolate a suspected order-flake
pytest -p randomly        # random order — if green here flips to red, you have hidden coupling
pytest --durations=10     # 10 slowest tests — find what makes the suite too slow to run locally
pytest --cov=src --cov-fail-under=85   # coverage gate; nonzero exit if below threshold
mypy --strict src/        # type gate; must be clean to merge
```

What the output tells you:

| Command | Read it for |
|---|---|
| `pytest -x --lf` | Did the one thing you touched go green? Fastest red→green cycle. |
| `pytest -p no:randomly` vs `-p randomly` | Same result both ways = order-independent. A flip = order coupling. |
| `pytest --durations=10` | Slow tests that push the suite past "runnable locally"; candidates to speed up or mark. |
| `--cov-fail-under` | New code actually exercised; a passing suite with dropping coverage means untested paths. |
| `mypy --strict` | Type-level gaps the runtime tests won't catch. |
