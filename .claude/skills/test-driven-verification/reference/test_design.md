# Test Design

Covers what to test and how to design the tests — deriving cases from acceptance criteria, the test pyramid, property/table/fuzz testing, fixtures vs mocks, and what to leave untested. Load this when deciding which tests to write before coding, or when reviewing a test suite for the right shape and the right assertions.

## Doctrine

> Test the behavior and the contract, not the implementation. A good test fails the moment the behavior breaks and survives any refactor that preserves the behavior.

- **Assert on observable contract** — return values, raised errors, persisted state, emitted events. Not on which private method ran or in what order.
- **One reason to fail per test.** If a test breaks, its name should tell you what behavior regressed.
- **Refactor-proof.** Rename internals, swap a data structure, inline a helper — green should stay green.
- **Derive from the spec, not the code.** Write the case from the acceptance criterion; if you can only write it by reading the implementation, you are testing the implementation.

See [red_green_loop.md](red_green_loop.md) for the order you write these in, and [evidence_capture.md](evidence_capture.md) for proving they ran.

## The test pyramid

| Layer | What it covers | Rough proportion | Speed | When to add |
|---|---|---|---|---|
| Unit | One function/class in isolation; pure logic, branches, edges | ~70% | <10ms | Default. Every behavior with logic. |
| Integration | Real collaborators across a boundary — DB, HTTP handler + serializer, two modules | ~20% | 10ms–1s | When a bug could only live *between* units (wiring, schema, contract drift). |
| E2E / system | Full stack through the real entry point (CLI, browser, API) | ~10% | seconds+ | One happy path per critical user flow. Smoke, not coverage. |

Bias hard toward many fast unit tests. Push a test down the pyramid whenever the same assurance is cheaper a layer lower. E2E is for "the pieces are wired together," not for exercising every branch.

## Deriving cases from an acceptance criterion

For each criterion, write four kinds of case:

| Kind | Question it answers |
|---|---|
| Happy path | Does the intended behavior work on valid input? |
| Boundary / edge | What happens at the limits — empty, zero, max, off-by-one, duplicate, unicode? |
| Error / failure | Does invalid input fail loudly and correctly (right exception, no partial write)? |
| Invariant preservation | What must stay true regardless of input? (totals balance, output sorted, idempotent) |

**Worked example.** Criterion: *"`apply_discount(price, pct)` reduces price by pct%, rejecting pct outside 0–100."*

```python
def test_applies_percentage():                 # happy
    assert apply_discount(100, 20) == 80
def test_zero_and_full_discount():             # boundary
    assert apply_discount(100, 0) == 100
    assert apply_discount(100, 100) == 0
def test_rejects_out_of_range():               # error
    with pytest.raises(ValueError):
        apply_discount(100, 150)
def test_never_increases_price():              # invariant
    assert apply_discount(100, 30) <= 100
```

## Property-based testing for invariants

Example tests check points you thought of; **property tests** check a rule across hundreds of generated inputs and shrink failures to a minimal counterexample. Reach for them when a *general law* holds: round-trip (`decode(encode(x)) == x`), idempotence (`sort(sort(x)) == sort(x)`), commutativity, "output always sorted," "never raises on valid input."

```python
# Python — hypothesis
from hypothesis import given, strategies as st

@given(st.lists(st.integers()))
def test_sort_is_idempotent(xs):
    assert sorted(sorted(xs)) == sorted(xs)

@given(st.binary())
def test_codec_round_trips(b):
    assert decode(encode(b)) == b
```

```typescript
// TypeScript — fast-check
import fc from "fast-check";

test("encode/decode round-trips", () => {
  fc.assert(fc.property(fc.string(), (s) => decode(encode(s)) === s));
});
```

Property tests beat examples when the input space is large or adversarial and a single rule must hold everywhere. They are weak when there is no clean invariant — then table-driven examples are clearer.

## Table-driven tests

Collapse many similar cases into one parametrized test so each row is a labeled data point, not duplicated code.

```python
# pytest
@pytest.mark.parametrize("text, expected", [
    ("",        0),
    ("a",       1),
    ("a b c",   3),
    ("  x  y ", 2),
])
def test_word_count(text, expected):
    assert word_count(text) == expected
```

```typescript
// vitest / jest
it.each([
  ["",        0],
  ["a",       1],
  ["a b c",   3],
])("counts words in %j", (text, expected) => {
  expect(wordCount(text)).toBe(expected);
});
```

## Fuzzing untrusted input

For parsers, deserializers, and protocol handlers exposed to untrusted bytes, fuzzing throws mutated/random input at the code to surface crashes, hangs, and memory bugs no example would think of. Use coverage-guided fuzzers — `atheris` (Python, libFuzzer-backed), `libFuzzer`/AFL++ for native, `fast-check` fuzz loops for JS. The target should never crash, hang, or corrupt state on any input — only reject it. Seed the corpus with real samples and keep it under version control.

## Fixtures vs mocks

Prefer real objects; substitute a **fake** (a working in-memory implementation) when the real thing is slow or external. Mock only at true system boundaries you cannot run in-process. Over-mocking produces tautological tests that assert the mock was called the way the code calls it — they pass even when the behavior is wrong.

| Prefer | Avoid |
|---|---|
| Real object under test, real pure collaborators | Mocking the class you are testing |
| In-memory fake (`SQLite`, fake clock, `tmp_path`) | Mocking a value object or simple data holder |
| Mock at the edge: network, wall clock, filesystem, randomness | Asserting on call order of internal methods |
| Inject the boundary as a dependency | `unittest.mock.patch` deep into private internals |

## What NOT to test

- Trivial getters/setters and pure pass-through delegation.
- Third-party or framework internals — assume the library works; test *your* use of it.
- Auto-generated code, constants, type definitions.
- Over-specified snapshots that pin exact whitespace/markup nobody asserts behavior on.
- Anything that just restates the implementation line-for-line.

## Anti-patterns

- **Testing private internals** — reaching past the public API; breaks on every refactor.
- **Snapshot overuse** — giant golden files blindly "updated" on failure; they assert nothing intentional.
- **Mock-the-thing-under-test** — stubbing the method you claim to verify; the test can never fail meaningfully.
- **Asserting on log strings** — coupling tests to human-readable messages instead of behavior or structured events.
- **Time/order/network flakiness** — real clock, real sleeps, unseeded randomness, shared global state between tests.

## Code-review checklist

- [ ] Does each test name a single behavior from a spec/acceptance criterion?
- [ ] Would it survive a behavior-preserving refactor of the implementation?
- [ ] Are happy / boundary / error / invariant cases all present for the criterion?
- [ ] Is the cheapest pyramid layer used for each assurance? No E2E doing unit work?
- [ ] Are mocks only at true boundaries (network, clock, fs, randomness)?
- [ ] Any invariant that should be a property test instead of three examples?
- [ ] Untrusted-input parser covered by a fuzz target?
- [ ] No assertions on logs, call order, or private state?
- [ ] No trivial-getter or framework-internals tests padding the count?
- [ ] Tests are deterministic — seeded RNG, injected clock, isolated state?

## Verification

Coverage shows what code was *exercised*; mutation testing shows what your tests actually *assert*. Use both — high coverage with weak assertions still lets bugs through.

```bash
# Python — line + branch coverage, fail under threshold
pytest --cov=pkg --cov-branch --cov-report=term-missing --cov-fail-under=85

# Hypothesis — confirm properties ran enough examples, inspect generation stats
pytest --hypothesis-show-statistics

# Mutation testing — do tests catch injected bugs?
mutmut run && mutmut results      # survivors = unasserted behavior
cosmic-ray exec config.toml session   # alternative, config-driven

# TypeScript / JS
vitest run --coverage              # exercised lines/branches
npx stryker run                    # mutation score: % of injected bugs killed
```

What to look for:
- **Branch coverage gaps** in `--cov-report=term-missing` — untested error paths and edges.
- **Surviving mutants** (`mutmut results`, Stryker score < ~80%) — code where flipping an operator or deleting a line still passes; that behavior is unasserted.
- **Hypothesis stats** showing too few examples or heavy filtering — the property barely ran.
- A green suite with low mutation score means the tests run the code but don't check it. Fix the assertion, not the coverage number.
