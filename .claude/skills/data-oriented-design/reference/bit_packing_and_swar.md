# Bit-packing & SWAR

Storing several values in the bits of one machine word, and operating on packed
data with whole-word arithmetic (SWAR — SIMD Within A Register). Load this for
flags/state words, compact records, free-list/allocation bitmaps, parsing, and any
"pack N values at different bit ranges and shift" task. The bit identities trace to
Warren's *Hacker's Delight*.

## Doctrine

A 64-bit word is 64 parallel bits you can set, test, and move with single
instructions. Packing related values into one word saves memory (fewer cache
lines), enables atomic multi-field updates (one CAS), and lets whole-word
arithmetic do field logic for free — *if* you choose the bit layout so the cheap
op means what you want.

## The bit toolbox (single-word identities)

| Idiom | Effect | Mechanism |
|---|---|---|
| `x & -x` | isolate lowest set bit | `-x = ~x+1` flips all bits up to & incl. lowest 1 |
| `x & (x-1)` | clear lowest set bit | borrow ripples through the trailing zeros |
| `!(x & (x-1))` | is-power-of-two (excl. 0) | only one bit set ⇒ clearing it gives 0 |
| `popcnt(x)` | count set bits | hardware instruction |
| `tzcnt(x)` / `ctz` | index of lowest set bit | for narrow widths OR in a guard bit first to define the zero case |
| `lzcnt(x)` / `clz` | leading zeros | |
| `clz(x) ^ (W-1)` | index of highest set bit (= `W-1-clz`) | XOR avoids the subtract |
| `(~0 << a) & (~0 >> (~b & (W-1)))` | mask of bits `[a,b]` | `~b & (W-1) == W-1-b`; double-shift window |
| `1<<W >> clz(x-1)` | round up to power of two | shift a top bit down by the leading-zero count |
| `bswap(x)` | reverse byte order | endianness without touching intra-byte order |

**Iterate a bitmask:** `while (m) { i = tzcnt(m); use(i); m &= m-1; }` — clear the
lowest set bit each step.

**Find a run of N set bits** by log-step self-AND: repeat `x &= x >> (n>>1)`,
halving `n` each step, leaving a 1 only where N consecutive bits were all set; mask
with `validBits` to constrain run starts to an alignment lattice.

## Branchless field assignment & select

- **Set or clear a bit/field by condition without branching** — compute both and
  select: `mTrue = x | mask; mFalse = x & ~mask; x = cond ? mTrue : mFalse;`.
- **Blend two words by mask:** `(a & ~mask) | (b & mask)` — the scalar form of SIMD
  `vpblendvb`; the workhorse merge for packed data.

## Packing many fields into one word (the case study)

Pattern from a userspace reader/writer lock that packs **reader count, writer flag,
spin flag, and a priority counter** into one `atomic<u64>`:

1. **Define each field's offset as a shifted constant:** `kRead = 1<<0` (bits 0–9),
   `kWrite = 1<<10`, `kSpin = 1<<11`, `kPrio = 1<<12` (bits 12–63).
2. **Extract a low field** by masking with `(next_field_bit - 1)` (all-ones below):
   `x & (kSpin-1)` yields reader+writer bits together.
3. **Mutate a sub-field with whole-word add/sub of its unit:** `state + kRead`
   increments the reader count; `fetch_sub(kWrite)` releases the writer — no
   read-modify-write of a masked region needed.
4. **Re-assemble with OR:** `kSpin | (prio - kPrio) | rw`.
5. **Choose positions so the cheap whole-word op is the field op you want.**
   Priority in the *top* bits means a plain `prio > state` compares priority — the
   low flag/count bits can't outweigh one `kPrio` step. *This is the key design
   move: pick bit ranges so integer compare / add / CAS do the field logic for
   free.*
6. **Atomicity for free:** the whole state transitions in one
   `compare_exchange` under the right memory order (`acquire` take / `release`
   release / `relaxed` retry). For the concurrency mechanics see
   `cpp-systems-internals` and `principal-production-engineer/reference/memory_data_ownership.md`.

Design tips: leave headroom so a field can't overflow into its neighbor; document
the bit map in a comment; prefer this over language bitfields (`int x:3`) when you
need defined layout, atomicity, or portability — bitfield layout is
implementation-defined.

## IEEE-754: a float is already a packed integer

Layout: `sign(1) | exponent(8) | mantissa(23)` for `float`. Treat it as a `u32`
(type-pun via `memcpy`, never a pointer cast — strict-aliasing-safe):
- **Exponent:** `(bits >> 23) - 127`. **Sign:** `bits >> 31` (or `bits << 31` to
  position it). **Mantissa:** `bits & 0x7FFFFF`, re-based by OR-ing a chosen
  exponent.
- **Order-preserving key transform** (for radix sort, `reference/algorithms_and_structures.md`):
  `key = (bits | 0x80000000) ^ (int32(bits) >> 31)` — for negatives the
  arithmetic-shift mask inverts all bits (reversing their order), for positives it
  just sets the sign bit; invert exactly on the way back.
- Vectorized transcendental kernels use the same unpacking for range reduction
  (extract exponent, polynomial on the mantissa, repack, blend in special cases).

## Multi-word bit arrays (packing many 1-bit values)

Bitset over `word[]` (each 64 bits):
- **Address:** `word = i >> 6`, `bit = i & 63`, set with `word[i>>6] |= 1ull << (i&63)`.
- **Mask the partial last word** so unused high bits never count:
  `lastMask = ~0 >> (-nbits & 63)` (negation gives the leftover count without a
  modulo); AND it into every popcount/scan/compare.
- **Whole-array shift = funnel shift across words:**
  `out[i] = (in[i-1] >> (64-s)) | (in[i] << s)` — bits that fall off one word feed
  the next. This is the cross-boundary shift packed multi-word values need.
- **Nth set bit** via popcount binary search (32→16→8→1, shifting down as it
  narrows); scan blocks with early-out, then one `tzcnt`/`lzcnt`.

## Multiply as parallel bit-scatter (advanced)

A single multiply can broadcast a small field to several bit offsets at once; mask
the wanted copies, optionally multiply again to gather them. Used in branch-free
bit-reversal and bit-gather tricks. Powerful but opaque — comment heavily and keep
a reference/test for it.

## Anti-patterns

- Language bitfields (`unsigned f:3;`) where layout/atomicity/portability matters —
  the bit order and packing are implementation-defined.
- Read-modify-write of a packed field with separate load/mask/or/store when the
  whole word could transition in one atomic op.
- Reinterpreting bits via `reinterpret_cast`/union punning instead of `memcpy`
  (UB / aliasing hazards).
- Clever multiply/scatter tricks with no comment and no test.
- Forgetting to mask the partial last word of a bitset (counting garbage bits).

## Code-review checklist

- [ ] Is the bit layout documented, with headroom against field overflow?
- [ ] Are packed multi-field updates atomic (one CAS) where concurrency requires?
- [ ] Are positions chosen so whole-word compare/add does the intended field logic?
- [ ] Is float↔int punning done via `memcpy`, and are key transforms inverted?
- [ ] Are bitset partial-word masks applied on every count/scan/compare?
- [ ] Are exotic bit tricks commented and covered by a test/oracle?

## Verification commands

```bash
objdump -d -C ./bin | less        # confirm shifts/and/or/cmov/lock cmpxchg, no hidden branches
perf stat -e instructions,cycles,branch-misses ./bench
# Correctness: exhaustive over the field domain (8/16-bit) or randomized + an oracle.
# Concurrency: run under ThreadSanitizer for the atomic-state word.
clang++ -fsanitize=thread ... && ./bin
```
Look for: the packed update compiling to a single `lock cmpxchg`/`xadd`; field
extraction as `and`/`shr` with no branch; randomized round-trip tests of pack/unpack
and of the float key transform passing against the oracle.
