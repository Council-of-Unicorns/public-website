# CHIP_SPEC.md — RPU v0.2 (builds on v0.1 spec notes)

Status: working spec. Every number below is output of the calibrated Tier-1 instrument
(measured RTX PRO 6000 anchors, P6 gate green; FP16→FP4 energy scale s = 2.6–3.4 MEASURED
via the FP8 capture; η = etch efficiency advantage over measured Blackwell — architecture-only
evidence band 1.6–3.2× per TPUv4-vs-A100, §6a/§7). v0.1's architecture ideas are kept; its
arithmetic is corrected where the instrument refutes it (§3).

## 1. System targets

- **Model:** DreamZero-class 14B DiT; d=5120, L=40, ffn=13824, heads=40; 4-bit weights (7.0 GB),
  FP8 activations; N_ctx = 18,720 tokens (2 s window), N_new = 1,560–3,120.
- **Form factor:** fanless robot head, **40 W chip power at the neck-path ceiling — power
  parity with Thor-in-head** (2026-07-29; the TDP ratio cancels, S = η exactly).
- **Success metric — SOLID beat at power parity (revised 2026-07-29, §A8a):** **S ≥ 2×
  vs Thor-in-head at the 5th percentile, in EVERY mode including Deadline**, and median
  S ≥ 2 — **both frozen at 2.0 in bench/contract.toml; the bar is on S, not on η**
  (clarified 2026-08-10: the derived figures below had crept into use as if they were
  bars). In the current model the p05-every-mode criterion derives **η* ≈ 2.15** and the
  median criterion **η* ≈ 2.05** (which alone is not a success claim — it leaves
  Deadline mode at 1.91× median); the **design target is η = 3** (solid even if Thor
  gets a 25% thermal-budget margin, 50 W → η ≥ 2.80). The derived solid
  requirement sits mid-band in the architecture-only evidence (1.6–3.2×) and the target at
  its top, so the stacked levers (realized-utilization edge — the TPU 80%-vs-37%
  latency-bound datum, uncredited in the fair headline — Ledger-B realization gains,
  sub-Vmin §6b) are margin, not load-bearing. The solid bar also now coincides with the
  Tier-2 kill criterion (η ≥ 2.2).
- **Stretch target:** absolute 200 ms chunk (5 Hz hard real-time) in Deadline Mode — at the
  measured s this requires **η ≈ 12**: out of evidence range for silicon alone. The 5 Hz
  absolute loop therefore needs model-side compression beyond the current workload (smaller
  model, fewer tokens, or a validated FP4-native training recipe) or a larger power envelope
  — a finding of the 2026-07-15 DVFS/FP8 measurements, not an assumption (§7).
- **Schedule:** 1–3 diffusion steps, **microcode-selectable** (not mask-fixed at 3; §5's mode
  table is why).

## 2. The latency equation — four bounds, not three

```
t_chunk = max( Compute, Memory-Transfer, Communication, ENERGY-DISSIPATION )
                                                        └── E_chunk / (TDP · (1 − leak))
```

v0.1's three-term equation omits the term that actually binds. A thermally capped head is an
**energy-rate-limited system**: a chunk that costs E joules cannot finish faster than E/TDP
seconds no matter how much silicon is present. At 40 W usable ≈ 36 W:

| bound (3-step CFG, N_new=3120, 4 PF array) | value |
|---|---|
| Compute / step (2.36e14 FLOPs @ 4 PF × 0.805) | 73.6 ms |
| Memory / step (14.8 GB @ 307.2 GB/s) | 48.1 ms |
| Communication (etched sequencer) | ~0 |
| **Energy / chunk (477 J @ η=1 → 161 J @ η=3, ÷36 W)** | **13,251 → 4,470 ms** |

Energy dominates by an order of magnitude. Consequently every efficiency decision (η) is a
*latency* decision, and the design centers on joules, not on peak anything.

**Regime honesty (added after the WAN-on-B200 memory-bound objection [F]):** the compute-vs-
memory margin above is thin, not vast — the candidate's ridge (~10,500) sits only ~1.5× below
the workload's fused intensity (~16,200), and hot-head refresh derating nearly closes it.
Which side of the ridge the REAL workload sits on depends on realized reuse and fusion —
measured memory-bound on B200 in the founder's own profiling. The three-wall ordering
(energy ≫ compute ≳ memory) holds in our model, but the memory terms are the least-anchored
numbers in it (no memory-bound calibration anchor exists yet). Full treatment, solution
ladder, and the gate-1 anchor requirement: [`MEMORY_BANDWIDTH.md`](MEMORY_BANDWIDTH.md).

## 3. Corrections ledger vs v0.1

| v0.1 claim | Corrected | Why |
|---|---|---|
| KV window held in on-chip SRAM ring | **KV lives in DRAM** (shift-in-place ring); on-die SRAM holds stream/window buffers only | the 2 s window is 2·18,720·40·5,120 B ≈ **7.7 GB** — no head-power SRAM exists at that size |
| 7 GB streamed per step → 22.8 ms | **14.8 GB per step → 48.1 ms** (weights 7.0 + KV 7.7 read each step) | attention reads the full window every step; P2: KV is a first-class term, ≈ the weight term |
| Compute ≈ 2 ms/step ("negligible") | **73.6 ms/step** (3-step CFG) / 18.4 ms (1-step N=1560) at 4 PF effective | the workload is **compute-bound**: intensity ≈ 16,000 FLOP/B vs ridge ≈ 10,500; 2 ms would require ~124 PF effective |
| Double-buffer: Bank A computes step N while Bank B prefetches step N+1 weights | **tile-granularity ping-pong** (2 × ~16 MB FIFOs feeding a weight-streaming systolic array) | step-granularity banks would need 2 × 7 GB of SRAM; weights are consumed as they arrive, never resident |
| Total 70.4 ms → "crushes the deadline" | see mode table (§5): 3-step CFG ≈ **4.5 s at η=3** (energy-bound) — misses 5 Hz but **beats Thor-in-head 2.86×** (≥ project success); 5 Hz approached only in Deadline Mode at η≈6.4 | the energy bound was missing; 5 Hz at 3-step/40 W would need ~12× better pJ/FLOP than measured Blackwell — beyond all evidence |

## 4. Memory architecture (v0.1's direction, kept and sized)

- **256-bit LPDDR5X @ 307.2 GB/s** — confirmed sufficient: the conveyor requirement at 4 PF is
  ~200 GB/s (stream one step's 14.8 GB inside its 73.6 ms compute), so LPDDR5X carries it with
  1.5× margin and no HBM cost/power. Capacity ≥ 16 GB (7.0 weights + 7.7 KV + activations/headroom).
- **Conveyor controller:** pure sequential prefetch, open-page burst streaming, identical
  address trace every chunk; no cache, no coherence. ECC on (safety-critical control loop).
- **Refresh is part of the etched schedule (new).** DRAM refresh is the classic determinism
  leak: opportunistic all-bank refresh locks the rank for ~hundreds of ns every tREFI≈3.9–7.8 µs
  and is why bounded-latency DRAM is hard in general-purpose systems (automotive LPDDR5 practice
  leans on per-bank/REFsb scheduling for exactly this reason). Our conveyor's address trace is
  static, and at 4 PF the stream occupies only ~65% of each step (48.1 ms of 73.6 ms) — so the
  **sequencer issues per-bank refresh commands in the known conveyor-idle windows**, per-bank
  rotation aligned to the trace. Refresh interference with the deadline is then **zero by
  construction, not bounded by analysis** — the same proof style as the zero-OS claim, extended
  into the DRAM. (This is only possible because the schedule is etched; a cache-based controller
  cannot know its future accesses.)
- **F2 shared weight stream (kept verbatim):** weights and context-KV fetched **once per step**,
  fan-out of 2 to both CFG branches in silicon — this is the modeled F2 rule; it halves external
  bandwidth demand exactly as v0.1 states.
- **KV ring:** DRAM-resident, shift-in-place via ring pointers at chunk end (no copy); the new
  chunk's KV appended by the write path; SRAM holds only in-flight window tiles.
- **INT2 weight option (flagged, not default):** step stream drops to 11.2 GB → 36.5 ms;
  quality risk owned by the model team; keep the dequant path format-flexible enough to try it.
- **Bandwidth headroom ladder:** if the memory-bound anchor forces it — wider LPDDR5X
  (Apple ships 546 GB/s on-package), LPDDR6 (~2.25×/package, 2026), LPDDR6-PIM (KV passes
  in-bank), 3D DRAM-on-logic (gen-2; 0.66–0.88 pJ/bit). Ratio re-provisioning (MACs↔channels)
  is a gate-1 decision. See [`MEMORY_BANDWIDTH.md`](MEMORY_BANDWIDTH.md).

## 5. Operating modes (instrument-verified at the MEASURED s = 3.0)

**Quality is the flagship mode** — the headline numbers quote it — and the solid
criterion still requires every mode to clear 2×. (40 W parity, 2026-07-29.)

| Mode | Schedule | Chunk @ η*=2.15 (derived solid criterion) | @ η=3 (target) | vs Thor-in-head (η*=2.15/3) | 200 ms deadline |
|---|---|---|---|---|---|
| **Quality (flagship)** | 3-step CFG, N_new=3120 | 6.21 s | 4.47 s | **2.13× / 2.97×** | misses |
| **Balanced** | 2-step CFG, N_new=3120 | 4.14 s | 2.98 s | 2.13× / 2.97× | misses |
| **Deadline** | 1-step distilled, N_new=1560 | 540 ms | 395 ms | 2.09× / 2.87× | needs η≈6.4 |

*(Historical: the earlier s=10 table met the deadline at η≥5; the measured FP16→FP8 ratio
of 1.77× — not the naive 2× per halving — moved s from an assumed ~10 to ~3, tripling
absolute energies. Relative speedups are s-insensitive and improved slightly.)*

Implications the silicon must honor: (a) the schedule sequencer is a small **microcode ROM**,
not a hardwired 3-step FSM — all three modes on one chip; (b) the control stack replans at
chunk rate, so Quality mode at ~0.5–1 Hz replan remains usable for non-deadline tasks while
Deadline mode serves the 5 Hz loop; (c) the SOLID success metric (p05 S ≥ 2× in every
mode; the frozen bar) derives η* ≈ 2.15 in the current model, with η = 3 as the margin
design target — the absolute 5 Hz goal
remains the separate stretch that motivates step-distillation quality work in parallel.

## 6. Compute datapath

- **~1.9 M FP4 MACs @ ~1.05 GHz** (4 PF dense). The clock is set by the deadline, not by
  peak: stretch-to-deadline sizing. NOTE (supersedes v0.2 text): the DVFS sweep showed the
  voltage lever is NOT available inside standard operating envelopes (§7.1) — η must come
  predominantly from architecture; sub-Vmin operation is a separately-gated reopened bet (§6b).
- Weight-streaming systolic tiles matched to (d=5120, ffn=13824); attention runs on the same
  fabric in two passes with an **online-softmax streamer** between them (see CHIP_LAYOUT §3).
  State of the art for etched attention datapaths — adopt at Tier-2 evaluation:
  **FLASH-D** (softmax division hidden inside sigmoid evaluation, dynamic max-tracking
  removed: −22.8% area, −20.3% power in a 28 nm ASIC, [arXiv:2505.14201]) and **fused
  ExpMul** exponential-multiply operators ([arXiv:2505.14314]). Our fixed geometry adds one
  further option no GPU kernel has: with known FP8 input scales, the softmax max-bound can be
  **static (precomputed per layer), eliminating the online max recurrence entirely** — a
  candidate simplification to check against task accuracy at gate 1.
- **Accumulator precision — RESOLVED by TPU lineage:** FP8 products accumulate into **FP32
  accumulators held in a dedicated accumulator SRAM below the array** (TPUv1's exact pattern:
  16-bit products → 4 MB of 32-bit accumulators; accumulator traffic ≪ operand traffic, so
  the wide format costs little). FP16 accumulate remains a task-checked fallback (§6a.5).

  **REOPENED 2026-08-04 — "costs little" is wrong at FP4.** The TPUv1 reasoning holds for
  16-bit products. At FP4 the multiply is tiny and the asymmetry inverts: a 32-bit
  accumulator read-modify-write costs ~0.020 pJ against what we had called a "0.0156 pJ
  FP4 multiply." **Corrected 2026-08-05: that 0.0156 was itself a scaled 16-bit INT *MAC*
  (Accelergy's 3.0 pJ, accumulate included, x(4/16)^2 /12), so adding an accumulator on
  top double-counted it — and the quadratic width rule was applied at INT width 4 when an
  E2M1 multiply has a 2-bit significand.** Redone from Horowitz 45 nm primitives
  (sig-mult 2bx2b + 3b exponent add + normalize, /8-/12 node scaling): multiply
  ~0.0032-0.0048 pJ, naive 32-bit accumulate ~0.0083-0.0125 pJ — the accumulator is
  ~2.6x the multiply, still the largest single term in arithmetic energy
  (~56 %). Narrow-multiply/wide-accumulate is still right; pricing the wide side as
  negligible is not.

  Two levers, and they stack [T, component energies from Accelergy 45 nm scaled to 5 nm]:

  | Lever | Effect on arithmetic energy |
  |---|---|
  | **Adder tree**: combine 8 products combinationally, one register update per 8 MACs | 0.51x |
  | **Narrower accumulation**: BF16, or INT8 with block scale (the MXFP4 scales already exist) | accumulator halved to quartered |
  | **Both** | **2.1x lower; accumulator falls from 56 % to 7 % of arithmetic energy** |

  The adder tree spends combinational depth to buy this, which costs clock frequency. At
  1.05 GHz wide-and-slow we have the timing budget, so the trade is close to free for us
  and would not be for a high-clock part. Narrowing the accumulator is a numerics risk in
  a different category from the recorded no-aggressive-quantization constraint (that
  covers INT2 weights, FP4 KV and 2:4 pruning), but it still requires task-accuracy
  validation before adoption. **Gate-1 decision: adder-tree width, and accumulator format.**
- **Hardwired FP4-dequant → FP8 path** into the array; no format kernels, no register-file
  trips. **Weight format: microscaling, two profiles.** Default **MXFP4** (32-element blocks,
  E8M0 power-of-two scales) — dequant is an **exponent add, zero multipliers**, the cheapest
  possible dequant row. Fallback **NVFP4** (16-element blocks, FP8-E4M3 scales) where task
  accuracy demands finer grain — costs one FP8 multiply per block. The dequant row supports
  both plus INT4/INT2 (§4); profile is a µcode field, not a mask decision.
- **Zero-OS execution (kept verbatim):** no kernel launches, no interrupts; the etched sequence
  + bounded DRAM access patterns are what make deadline-miss-rate < 10⁻⁴ *provable*, not just
  observed. µcoded update engine (flow-ODE / CEM, ~2 % datapath) is the one programmable island.
  *Why this matters most in our regime — the strongest published datapoint:* under a hard
  latency bound, deterministic scheduling degrades gracefully while dynamic scheduling
  collapses. The TPUv1 paper measured exactly this — held to a 7 ms p99 response limit, the
  **TPU sustained 80% of peak throughput while the same-node K80 GPU fell to 37%** (and the
  CPU to 42%) [X: Jouppi et al., ISCA 2017]. A 5 Hz / 200 ms control loop is a *tighter*
  latency-bound regime than that benchmark, so the determinism advantage is not a rounding
  term — it is a first-class source of realized throughput, on top of the per-op η.

## 6d. The µcode toolchain — our XLA analog (who produces the etched schedule)

TPU-class ahead-of-time scheduling (technique #5) works because a *compiler* regenerates the
schedule when the model changes; the TPU keeps a general compiler (XLA) because it serves all
of Google's models. We serve one model family, so "compiler output" collapses to a **static
image loaded at boot** — but something must produce that image. That tool is a first-class
deliverable, not an afterthought:

**`rpu-schedule` (offline, host-side):** model checkpoint → schedule image. Stages:
1. **Ingest** the workload as `WorkloadParams` (already the simulator's contract) — shapes,
   step count, precision, N_new, KV geometry.
2. **Tile & allocate** — map GEMMs/attention to the 120-tile fabric, size FIFO/spine buffers,
   place accumulators. The **Tier-1 simulator is reused verbatim as the cost model** here
   (roofline + energy + the deadline check) — the instrument we already trust to predict the
   chip becomes the thing that schedules it. Tier-2 refines the mapping once it exists.
3. **Sequence** — emit the µcode ROM image: per-step DMA descriptors (the conveyor's static
   address trace), refresh-command placement in idle windows (§4), dataflow selection per
   pass (GEMM vs attention, per CHIP_LAYOUT §6), and the mode table (Quality/Balanced/Deadline).
4. **Fold in the B-lever static profiles** (PERF_LEVERS): sliding-tile masks, token-merge
   permutations, per-layer cache/skip schedules, cross-chunk reuse thresholds + the reserved
   worst-case Deadline slots.
5. **Emit the deadline certificate** — the worst-case cycle count per mode that the miss-rate
   proof consumes. A schedule that cannot certify its mode's deadline fails to build (the P6
   discipline, moved into the toolchain).

**What this answers:** (a) *model revisions* — a new checkpoint is a re-run of `rpu-schedule`,
not a re-spin, as long as it stays inside the mask-fixed envelope (shapes, layer count, tile
geometry); weights, scales, token counts, schedules are all image-loadable. (b) *the "what's
your compiler story" question* — this is it, and it reuses the calibrated instrument as its
cost model, which is a moat, not a cost. (c) *the co-design loop* — the model team's
distillation / sparse-fine-tune / trained-reuse-floor work (PERF_LEVERS B3/B7) feeds this tool
directly; the founder's train-time chunking and the schedule generator are two ends of one
pipeline.

**Mask-fixed vs image-loaded (the revision contract):**

| Mask-fixed (re-spin to change) | Image-loaded (`rpu-schedule` re-run) |
|---|---|
| tile count/geometry, d/ffn divisor structure | weights, MX/NVFP4 scales, INT2 option |
| accumulator width, dequant-row formats supported | diffusion step count (1–3), N_new, mode table |
| the update-engine ISA (primitive set) | update-engine *program* (flow-ODE vs CEM) |
| memory channel count, SRAM sizes | conveyor address trace, refresh placement, B-lever profiles |

### 6.0 What is and is not a differentiator  *(added 2026-08-04)*

Verified against the baseline rather than asserted, because three claims we had been
leading with do not survive the check:

| Claim | Status |
|---|---|
| Fused / non-materialized attention scores | **not a differentiator.** FlashAttention is the PyTorch SDPA default and our own measured anchors used it. |
| FP8 attention, FP4 linears | **not a differentiator.** Blackwell has both natively. |
| Zero-instruction control path | **parity, not advantage.** TPUv1 already banked this in 2015 with a small CISC set where one instruction drives a whole dataflow; modern tensor cores amortize fetch across thousands of MACs. |

What survives is implementation efficiency inside the same overhead budget: no
tensor-core-to-vector-unit handoff for softmax, K and V streamed from the conveyor rather
than through shared memory and the register file, a static per-layer max bound, and the
cache hierarchy removed entirely. All of it shows up as f_ours in η = f_ours / f_gpu, and
none of it is a separate multiplier.

The honest position: a well-executed TPU-class design with a better attention datapath
lands somewhere in the published 1.6-3.2x band, and the derived solid-criterion η* of
2.15 (the frozen bar itself is S ≥ 2) sits inside it.
We need the upper half of that band, not the band plus a bonus.

## 6a. Design principles adopted from Hameed et al., ISCA 2010 ("magic instructions")

The canonical quantitative study of the processor→ASIC gap (720p H.264 encoder, Tensilica
CMP): baseline FU energy is **5.8% of total** (~140 pJ/instruction overhead vs ~100s fJ of
math); SIMD buys 7×, op-fusion only 1.4× more, and **custom storage wired to multi-input
functional units** buys the remaining ~18×, landing within 3× of full ASIC with FU fraction
at **35%**. Principles we adopt, each traceable to a mechanism in that paper:

1. **Custom storage over addressed SRAM wherever access order is known.** The KV window
   advances monotonically → KV stream buffers are **shift/FIFO structures wired into the
   attention array**, not addressed reads (their FME 6-entry shift-FIFO + carry-save
   multi-input adder: "<1/30th the energy of a traditional approach"). Same pattern for
   Q-reuse across KV shifts (their 4-direction-shift SAD registers, 256 ops/cycle).
2. **FU-energy fraction is the gate diagnostic.** Their ladder (5.8% → ~10% → 35% → ASIC)
   becomes our Tier-2 metric: the phase-1 datapath model must show **FU fraction ≥ 35%**;
   η rises with it. Since tensor cores already are "magic instructions" for GEMM, our η
   must come from the fabric AROUND the MAC (their ledger: pipeline+clocking 22%, caches
   19%, RF 10% — the TPUv4 register-file finding in different clothes).
3. **Control fusion for the update engine.** Their CABAC lesson: after the data-parallel
   path speeds up 100×, the control-dominated residue dominates, and the fix is collapsing
   inner control loops into **single constant-time instructions** (their
   BIARI_ENCODE_PIPE_5). The flow-ODE/CEM µcode exposes constant-time fused primitives,
   never a general vector ISA — which also preserves the determinism proof.
4. **Amdahl tail check (phase-2 gate).** At η ≈ 3 on the matmul path, the serial residue
   (flow update, action head, sequencing) is the next bottleneck; the per-operator energy
   table must be re-examined at each gate, not only the headline.
5. **Task-checked reduced precision is legitimate ASIC territory.** They computed
   distortion on 5 of 8 pixel bits (−30% energy, negligible SNR loss) — the pattern for
   our FP16-accumulate and INT2-weight decisions: allowed iff the task-success check
   passes, exactly like their SNR gate.
6. **Slight over-flexibility is worth it** — their explicit recommendation to make magic
   hardware "slightly more flexible than required... to increase the probability of it
   still being useful if the algorithm changes" is the Part-C programmable island (~1%
   cost), stated in 2010.

*(Source: Hameed, Qadeer, Wachs, Azizi, Solomatnikov, Lee, Richardson, Kozyrakis,
Horowitz — "Understanding Sources of Inefficiency in General-Purpose Chips," ISCA 2010.)*

## 6b. The voltage lever, reopened as a gated bet (sub-Vmin technique menu)

Our DVFS sweep proved the V² win is unreachable *within GPU operating envelopes* (§7.1) —
the silicon sits at its voltage floor. It did NOT prove sub-Vmin design is impossible; it
proved it requires custom techniques. Two developments justify keeping a **gated** phase-1b
work item: Etched now claims **"Low-Voltage Inference" in working A0 silicon** — math blocks
below half conventional voltage, with a published co-design cost list (splittable math
arrays, custom PDN/VRM, packaging/cold-plate co-design); and the near-threshold literature
provides a concrete technique menu with measured gains:

| Technique | What it does | Evidence class |
|---|---|---|
| Split voltage domains (logic near-threshold, SRAM higher) | logic MEP sits near Vth; SRAM MEP is higher — never drag SRAM down with the fabric | NTC literature; already our domain plan (CHIP_LAYOUT §4) |
| 8T/10T SRAM cells + read/write assist | 6T fails static-noise margin below ~0.6 V; 8T decouples read path | demonstrated to 0.26 V (64 kb 8T) |
| ~~In-situ timing-error detection (Razor-class)~~ **REFUTED 2026-08-04** | The 47 % was recovery *vs signoff margins*, not energy per inference. Measured on a 16 nm ZCU102 across 5 CNNs, normalized GOPs/J goes **1.00 at Vmin, 0.75 at 560 mV, 0.75 at 540 mV** — underscaling past Vmin is energy-*negative*. Chip-to-chip Vmin spread (31 mV) exceeds the exploitable window (30 mV). And recovery is a **replay**, i.e. variable latency, which is structurally hostile to a provable < 1e-4 deadline-miss bound. | [X*] **rejected** |
| Canary / tunable-replica / CPM adaptive voltage scaling | The version that actually shipped: POWER7 recovered 113–152 mV for **−20 to −24 % chip power** at no perf loss and 0.2 % area; AMD 28 nm 7–15 %; Qualcomm 16 nm 13–30 % throughput at 5–13 % energy with **no per-part test calibration**; Intel 22 nm improves from +14 %/−3 % at 1.0 V to **+31 %/−15 % at 0.6 V**, so it *composes* with undervolting | [X*] shipped silicon |
| Canary/monitor circuits + per-tile AVS | track droop and aging without global guardband | standard practice |
| Splittable/segmented MAC arrays | contain voltage droop blast radius; Etched's own named mechanism | vendor-claimed (A0) |

**Status: NOT counted toward the frozen 2.0 bar or its derived η* requirements.** The
headline bet remains architecture-only. Gate: a test-structure tile on the gate-4
shuttle, not before.

**Sizing corrected 2026-08-04 — the honest number is ~1.5×, not ~2.5×, and it is logic-only.**
The canonical 10× (Dreslinski 2010) rests on two 130 nm sensor chips that measured 6.6× and
9.8× at 9–11× frequency loss. The FinFET simulation figure is 8.2× at 7 nm — but that is a
31-stage FO4 inverter chain with no SRAM, no clock tree and no NoC. **The measured-silicon
number for a real DNN accelerator with SRAM and NoC (TSMC 16 nm, 0.41–1.2 V) is ≈3.3×
corner-to-corner for ≈11× frequency** [X*]. The simulation-to-silicon gap is ~3×, and it comes
from exactly the parts the FO4 chain omits.

At *fixed throughput* it is smaller again, because N× array width is N× the leaking
transistors and FinFET's low DIBL (22 mV/V at 7 nm vs 171 mV/V planar) means undervolting
barely reduces per-transistor leakage:

| Move | Array width | Net @ 20 % leakage | Net @ 30 % leakage |
|---|---|---|---|
| 0.85 → 0.62 V | 1.5× | **1.64×** | 1.54× |
| 0.85 → 0.52 V | 3× | **1.70×** | 1.43× |
| 0.85 → 0.41 V | 10× | 1.13× | **0.83× — worse than nominal** |

**The model changes sign between a 20 % and a 30 % leakage fraction, and a fanless hot head
is exactly the high-leakage regime.** Make the nominal-point leakage fraction a load-bearing
Monte Carlo input, not a constant. Recommended stopping point: **~0.55–0.6 V and 2–3× width**
— 0.62 V and 0.52 V land within 5 % of each other, so the aggressive end buys almost nothing
for a lot of area, yield and PDN current. SRAM pins the floor near 0.5 V regardless (N5 Vmin
improvement over 7 nm is "very little" without write assist), which is why Etched's phrasing
is *"math blocks"* below half voltage: that is a **dual-rail split**, and it is the right answer.

**Then derate for the memory wall.** This is a lever on the *logic* rail only. LPDDR5X PHY
runs at a fixed VDDQ and cannot be voltage-scaled at all, and our own non-negotiables say
7 GB streams from DRAM every step. If DRAM and PHY are 50–70 % of system energy, **a 1.5×
logic win is a 1.15–1.25× system win.** Score it against the compute budget, never the total.

This *explains* the P6 DVFS-flat result rather than contradicting it: a GPU cannot go there
because its SRAM, cell libraries and clock distribution pin it at its floor. But sub-Vmin
silicon buys ~1.2× at system level, not the ~2.8× that η* needs. **It is a contributor to
η*, not a solution to it.**

## 6c. Workload-shaping levers (Ledger B)

The absolute 5 Hz goal is attacked by shrinking the work, not only the joules-per-op: see
[`PERF_LEVERS.md`](PERF_LEVERS.md) (v2, post-scrutiny) — **≈1.4–2.6× (Deadline mode) /
1.7–3.8× (Quality mode)** chunk-energy reduction. Flagship lever after scrutiny:
**cross-chunk receding-horizon reuse** (WorldCache-class, 2.3× at 99.4% quality on a real
video world model), with per-step caching REFUTED for few-step schedules. Each lever is
task-success-gated and mapped to its etch mechanism; Deadline mode reserves worst-case
slots so dynamic reuse saves energy without touching the miss-rate proof.

## 7. Standing verification gates (before RTL)

1. **DVFS sweep — DONE 2026-07-15, adverse.** η_vf = **1.00×** within the GPU's envelope:
   pJ/FLOP is flat from 1.0–3.09 GHz (the card sits at its voltage floor; power scales
   ~linearly with clock). The wide-and-slow lever is NOT available via operating point on
   this silicon; any V² gain now requires sub-Vmin custom design — reclassified from
   "measured share of η" to "unproven custom-silicon claim." η must come predominantly
   from architecture (TPUv4-class evidence: ~1.6–3.2×). Data: `fixtures/dvfs_sweep.json`.
2. **FP8 capture — DONE 2026-07-15.** Measured FP16→FP8 energy ratio **1.77–1.82×**
   (not 2×). Speedup prior updated to s ~ U(2.6, 3.4) in `rpu/speedup.py`; §1/§5 numbers
   re-derived. Remaining prior: one FP8→FP4 step.
3. Tier-2 (Accelergy-class) energy model of one MAC tile + conveyor → computes the
   architecture share of η; gate: **η ≥ 2.2 evidenced AND FU-energy fraction ≥ 35%**
   (the Hameed diagnostic, §6a) before phase-2 commitments.
4. Deadline-mode existence proof: distill DreamZero to 1-step/N_new=1560 and show task-success
   holds — the algorithmic twin of the η bet; without it, Deadline Mode has no workload.
