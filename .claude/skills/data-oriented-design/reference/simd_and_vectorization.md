# SIMD & vectorization

The idiom catalog for processing many elements per instruction. Load this at rung
6 when a hot loop is data-parallel and memory/compute-bound. Prefer letting the
compiler auto-vectorize (see `control_flow_and_branchless.md` for the
preconditions); reach for intrinsics/assembly only when it can't, and **always
benchmark the vector version against the scalar baseline**.

## Doctrine

SIMD multiplies throughput by the lane count *only if* the data is contiguous,
aligned, branch-light, and dependency-free. The skill is (1) writing loops the
auto-vectorizer accepts, and (2) when hand-writing, knowing the handful of idioms
that turn lane-parallel results back into scalar answers.

## The core search idiom: broadcast → compare → movemask → ctz

To find/match a value across a vector of lanes:
1. **Broadcast** the query into every lane (`_mm_set1_*` / `vpbroadcast*`).
2. **Vector-compare** equal (or `min`/`max`/`cmpgt`) against loaded data.
3. **`movemask`** the per-lane result into an integer bitmask (one bit per lane).
4. **`tzcnt`/`ctz`** the mask for the first matching lane; `popcnt` to count
   matches; test-nonzero for "any match."

This is how an open-addressed hash table scans a bucket and how a fast `find`/
`contains` scans an array.

## Deferred reduction: OR many masks, test once

In a wide scan, do **not** branch after every vector. Process several vectors per
iteration (e.g. 8 vectors = a cache-line group or more), **`OR` all the compare
masks together**, and do a **single test+branch** per group. The independent
compares fill the pipeline; the one branch is amortized over dozens of elements.
Only on a hit do you redo the work to localize the exact element. This is the
structure of a high-throughput `find`/`contains` kernel.

## Packing lane results into a scalar word

When several `movemask`s must combine into one index space, **pack them into one
wide integer at byte offsets** and do a single `ctz`:
```
mask64 = m0 | (m1<<8) | (m2<<16) | ... | (m7<<56);   // 8 lanes × 8 vectors
index  = base + tzcnt(mask64);
```
On targets without a native `movemask`, emulate it with a shift-right-accumulate
sequence that gathers each lane's top bit into contiguous bits (NEON pattern).
(See `reference/bit_packing_and_swar.md` for the bit mechanics.)

## Running argmax / argmin (extremum *with index*)

Carry a running value vector **and** a running index vector:
1. `max`/`min` the new data into the value vector.
2. **`cmpeq`** to mark the lanes that just changed (new == updated value).
3. **`blend`** (`vpblendvb`) the *current positions* into the index vector at those
   lanes.
Maintain a per-lane position vector advanced by the lane count each iteration (add
a constant). At the end, **horizontally reduce** and break ties deterministically
(e.g. lowest index on equal via a `cmpgt`+blend).

## Horizontal reduction ladder

Collapse a vector accumulator to one scalar in `log2(lanes)` steps, carrying any
companion (index) vector through the same folds:
`vextracti128` (split 256→128) → `unpckhqdq` (fold 128→64) → `movshdup`/`shuffle`
(fold 64→32), applying the value op and a paired blend at each step.

## `pshufb` as a 16-entry parallel LUT

`_mm_shuffle_epi8` looks up 16 bytes in parallel from a 16-entry table indexed by
the low nibble of each byte. Use it for nibble/byte transforms (e.g. per-byte bit
reversal: split into nibbles `&0xF` and `>>4`, map both through reversed-nibble
tables, recombine). A SIMD-width table lookup with no branches.

## General rules

- **Align** data to the lane width (`alignas(32)` AVX2, `alignas(64)` AVX-512);
  prefer aligned loads; broadcast scalars once outside the loop.
- **Annotate non-aliasing** (`__restrict` / non-overlapping spans) so the compiler
  may vectorize and so hand-SIMD is safe.
- **Handle the tail** with a scalar (often `cmov`-based) remainder and small-`n`
  with a separate path or jump table — don't force the vector loop to handle 0–k
  elements.
- **Keep a scalar baseline and dispatch by ISA** at runtime (detect AVX2/NEON);
  the scalar path is the correctness oracle and the portability fallback.
- **Gather/scatter are slow** — prefer contiguous loads; restructure data (SoA) to
  avoid gathers rather than using gather instructions.

## Anti-patterns

- Hand-writing intrinsics where `-O3` + clean loop shape already auto-vectorizes
  (verify with the vectorization report first).
- Branching inside the vector body (forces scalarization) — use blend/mask.
- Per-element gather when an SoA reshape would make the load contiguous.
- Shipping a vector path with no scalar baseline to A/B against or fall back to.

## Code-review checklist

- [ ] Did the compiler actually vectorize (report checked), or is hand-SIMD
      justified by a measured failure to?
- [ ] Are loads aligned and contiguous; are gathers avoided via layout?
- [ ] Is the per-element work branch-free (blend, not `if`)?
- [ ] Is there a scalar baseline + ISA dispatch, and does the vector path match it
      bit-for-bit (or within a stated tolerance) on a correctness gate?
- [ ] Is the tail / small-n handled without penalizing the main loop?

## Verification commands

```bash
clang++ -O3 -Rpass=loop-vectorize -Rpass-missed=loop-vectorize ...   # did it vectorize?
g++    -O3 -fopt-info-vec-all ...
objdump -d -C ./bin | less          # confirm vp*/ymm/zmm ops at the hot site
perf stat -e instructions,cycles,fp_arith_inst_retired.* ./bench     # IPC, SIMD retired
# microbench scalar vs vector with the harness in measurement_and_verification.md
```
Look for: vector ops (`ymm`/`zmm`) and a higher IPC at the hot site; the vector
build beating the scalar baseline on wall-clock by ~lane-count (minus tail/overhead)
while passing the correctness gate.
