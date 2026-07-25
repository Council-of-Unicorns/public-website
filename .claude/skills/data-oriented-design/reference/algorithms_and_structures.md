# Algorithms & data structures for the access pattern

Choosing the structure and algorithm that fit the data and the hardware. Load this
at rung 1 of the optimization order — before any micro-optimization. The right
choice here dwarfs every later trick.

## Doctrine

The fastest code respects two things at once: **asymptotic complexity** and
**memory access pattern**. A theoretically-optimal algorithm with random pointer
chasing often loses to a "worse" one that streams contiguous memory. Pick the
structure whose hot operation is both low-complexity *and* cache-friendly.

## Hash tables — open addressing, SIMD-scannable

For fixed or bounded key sets on a hot path, prefer an **open-addressed table with
linear probing in cache-line buckets**, not a chained `unordered_map`.

- **Layout:** SoA — separate `keys[]` and `values[]`, both aligned to a cache line.
  A probe streams only keys; values are pulled in only on a hit.
- **Bucket scan with SIMD:** broadcast the query key, vector-compare against a
  bucket of lanes, `movemask` the result, `ctz` to the matching slot (see
  `reference/simd_and_vectorization.md`). One or two cache lines per lookup, no
  pointer chasing.
- **Power-of-two capacity → mask instead of modulo:** `idx = hash & (cap - 1)`;
  compute the next power of two with `1 << (bitwidth - clz(n - 1))`.
- **Empty sentinel + early-out:** a reserved "empty" value ends a probe run — if a
  probe hits empty, the key is absent.
- **Avalanche the hash:** a multiplicative/xor-shift finalizer (Murmur3-style
  `x ^= x>>16; x *= C1; x ^= x>>13; x *= C2; x ^= x>>16`) so the low bits the mask
  selects are well mixed.
- **Pick load factor up front** (e.g. 80%) and **never resize** — fixed capacity
  gives stable addresses and zero hidden reallocation (see `reference/data_layout.md`).

When *not* to: huge/unbounded key sets needing growth, or pointer-stable iteration
under concurrent insert — then a different structure or a growable design applies.

## Sorting — radix/counting for fixed-width keys

For large arrays of fixed-width keys (integers, floats, fixed structs keyed by
them), an **LSB radix sort** (byte-wise counting sort, one pass per key byte) beats
comparison sort: **O(n · width)**, no comparisons, **stable**, and cache-friendly.

Counting-sort core, done well, per byte position:
1. **Histogram** the byte across all elements — and store counts *pre-scaled by
   element size* so they double directly as byte offsets later.
2. **Exclusive prefix sum** the histogram → each bucket's start offset.
3. **Stable scatter:** copy each element to its bucket cursor, bumping the cursor.
4. **Ping-pong** between two buffers (`pass & 1` selects src/dst) so no copy is
   needed between passes; a single final copy only if the byte count is odd.

**Make the key order-preserving once, at the boundary**, so the inner passes stay a
pure unsigned byte sort (see `reference/bit_packing_and_swar.md` §IEEE-754): signed
flips the sign bit; float does `(bits | 0x80000000) ^ (int(bits) >> 31)` with the
exact inverse afterward.

When *not* to: tiny n (insertion/`std::sort` win on overhead and branch
prediction), very wide/variable keys, or when a comparator is intrinsically needed.

## Choosing the container (quick map)

| Need | Prefer | Avoid |
|---|---|---|
| Ordered hot-path sequence | `vector` + one `reserve` | `list`/`deque` of nodes |
| Membership / lookup, bounded keys | open-addressed flat table | chained hash map |
| Sort fixed-width keys, large n | LSB radix sort | comparison sort |
| Stable handles into a moving set | array + generational handles | raw pointers |
| Phase-scoped scratch | arena/bump allocator | per-object new/delete |
| Small set of flags / membership over an index range | bitset / packed bits | `vector<bool>`-of-pointers, `set<int>` |

## Anti-patterns

- Reaching for a tree/map for "ordered" or "fast insert" without measuring against
  a sorted vector.
- Growable hash map on a hot path with a known bound — pay the fixed-capacity cost
  once instead.
- Comparison-sorting millions of `int`/`float` keys.
- Re-deriving the hash table's modulo with `%` when the capacity is a power of two.

## Code-review checklist

- [ ] Is the data structure's hot operation both low-complexity and contiguous?
- [ ] Hash table: open-addressed, power-of-two mask, SIMD/scan-friendly bucket,
      avalanche hash, fixed capacity?
- [ ] Sort: is a radix/counting sort applicable (fixed-width keys, large n)? Is the
      key transform order-preserving and inverted afterward?
- [ ] Are growth/resize and per-element allocation absent from the hot path?

## Verification commands

```bash
perf stat -e instructions,cycles,cache-misses,branch-misses ./bench   # IPC + miss profile
# A/B the structure choice against the obvious baseline; compare wall-clock + misses.
perf record -g ./bench && perf report     # confirm the hot operation is where you think
```
Look for: radix beating `std::sort` on large fixed-width arrays (fewer
branch-misses, higher IPC); open-addressed table showing far fewer cache-misses per
lookup than the chained map.
