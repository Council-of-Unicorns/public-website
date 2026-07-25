# Control flow & branchless code

Shaping control flow so the branch predictor and the vectorizer can do their best
work. Load this at rung 5 (branch behavior) when a profile shows `branch-misses`
hurting, or before vectorizing a loop. For the CPU mechanics (pipeline stages,
predictor accuracy, misprediction cost) load `cpp-systems-internals` →
`reference/cpu_pipelines_and_l1i.md`.

## Doctrine

A branch the CPU predicts correctly is nearly free; a mispredict costs **10–20+
cycles** (a full pipeline flush). Two moves: make branches **predictable**, or
**remove** them. But removing a *well-predicted* branch can be slower than keeping
it — so measure `branch-misses`, don't blindly de-branch.

## When to go branchless

| De-branch | Keep the branch |
|---|---|
| Data-dependent, ~50/50, unpredictable outcome | Highly predictable (loop guards, monotonic, rare error) |
| Inside a hot loop you want to vectorize | Cold path; predictability is high |
| Both sides are cheap to compute | One side is expensive (don't compute it speculatively) |
| `branch-misses` is a measured bottleneck | Branch isn't in the profile |

## Techniques

### Compute-both-and-select (predication)
Compute both results and pick with a mask or conditional-move instead of branching:
- Scalar: write it as a ternary / `min`/`max` so the compiler emits `cmov`/`minss`
  (`x = c ? a : b;`, `lo = max(lo, x)`).
- Bitwise select / **blend**: `result = (a & ~mask) | (b & mask)` where `mask` is
  all-ones/all-zeros. This is the scalar form of SIMD `vpblendvb`. (See
  `reference/bit_packing_and_swar.md` for `AssignBit`/`AssignMask`/`Blend`.)
- Caveat: predication evaluates *both* sides — only a win when both are cheap and
  the branch was unpredictable.

### Jump table over a branch tree
For dispatch on a small dense integer (opcode, small size class), use a computed
jump (table of targets) instead of a chain of compares — one indirect jump, not
log(n) predicted branches. A "fall-through" cascade of cases (Duff's-device shape)
handles a contiguous range of sizes with shared tails.

### Sort before branching
When a loop branches on a data-dependent predicate, **sorting the data first** can
be a net win purely because the predictor then sees long predictable runs — and it
unlocks vectorization. Measure: the sort cost must be less than the
misprediction cost saved.

### Lookup tables for small mappings
Replace a cascade of `if`/`switch` arms that map an input to an output with a
small precomputed table indexed by the input. Branch-free and cache-resident.

### Branch hints (sparingly)
`[[likely]]`/`[[unlikely]]`, `__builtin_expect`, profile-guided optimization — use
only for measured or structurally-obvious skew (e.g. the error arm). `ASSUME(x)` /
`__builtin_unreachable()` let the compiler delete impossible branches. Layout and
algorithm changes usually matter more than hints.

## Writing loops the vectorizer can take

A loop auto-vectorizes only if all hold (see also `simd_and_vectorization.md`):
- **Contiguous** data, **known/computable trip count** at entry.
- **No cross-iteration data dependency** (each iteration independent).
- **No input/output aliasing** — annotate non-overlapping pointers (`__restrict`)
  or pass non-overlapping spans.
- **No exceptions, opaque/indirect calls, or virtual dispatch** in the body — each
  blocks vectorization (exceptions constrain optimization *even when never thrown*).
- **Aligned** data when the lane width needs it.
Keep hot-loop nesting shallow (≤2), use guard clauses, and **split** a loop that
does different work under different conditions into separate passes rather than
branching per element.

## Anti-patterns

- De-branching a perfectly-predicted branch and *adding* work (both sides now
  always run).
- `std::function` / capturing-lambda / virtual call **per element** in an inner
  loop — an opaque indirect call that blocks inlining and vectorization.
- Early `break`/`return` inside a loop you want vectorized — split the loop instead.
- Deep `if`/`switch` nests doing unrelated work in one pass.

## Code-review checklist

- [ ] Are unpredictable, data-dependent hot branches converted to select/blend
      (and is the conversion measured to help)?
- [ ] Is small-integer dispatch a jump table, not a compare chain?
- [ ] Do hot loops avoid per-element opaque/virtual calls and exceptions?
- [ ] Are non-aliasing pointers/spans marked so the compiler can vectorize?
- [ ] Are branch hints reserved for measured/obvious skew, not sprinkled?

## Verification commands

```bash
perf stat -e branches,branch-misses,instructions,cycles ./bench   # misprediction rate, IPC
perf record -e branch-misses ./bench && perf report               # which branch
# Did it vectorize?  (compiler vectorization report)
clang++ -O3 -Rpass=loop-vectorize -Rpass-missed=loop-vectorize -Rpass-analysis=loop-vectorize ...
g++    -O3 -fopt-info-vec-all ...
objdump -d -C ./bin | less     # confirm cmov/vector ops / jump table at the hot site
```
Look for: `branch-misses` per branch dropping after de-branching; a vectorization
"missed" diagnostic naming the exact blocker (aliasing, call, exception); `cmovxx`
or `vpblendvb`/`vmaxps` replacing conditional jumps at the hot site.
