# PERF_LEVERS.md — workload-shaping ledger, v2 (post-scrutiny)

Companion to [`CHIP_SPEC.md`](CHIP_SPEC.md). The chip is **energy-rate-limited** (spec §2),
so every lever is scored by its reduction of **chunk energy** — that *is* speed at head
power. Tags: **[M]** measured here, **[S]** our instrument, **[X]** external literature,
**[T]** estimate/bet. **v2 is the adversarial-scrutiny pass**: each lever carries a verdict;
v1's numbers are corrected where they didn't survive.

Ledger A (architecture η, required 2.15 solid at 40 W parity [S], evidence 1.6–3.2× [X]) and Ledger C (sub-Vmin,
spec §6b) are unchanged. This file is Ledger B: levers that shrink the *work*.

## The v2 verdict table

| # | Lever | Verdict | v1 → v2 estimate (chunk-energy ×) | What scrutiny found |
|---|---|---|---|---|
| B1 | Diffusion feature caching across steps | **REFUTED for our schedule** | 1.3–1.7 → **1.0–1.2, Quality mode only; 1.0 in Deadline mode** | TeaCache-class gains are measured on 50-step schedules; the serving literature states directly that intra-request caching is **"ineffective on industrial 4-step distilled models"** [X, arXiv:2604.04451]. Our 3-step schedule is past that cliff; 1-step has nothing to cache across. Remnant: CFG-pair feature reuse (FasterCache-style) in Quality mode only. |
| B2 | Sparse video attention (sliding-tile class) | **SURVIVES, trimmed** | 1.3–1.6 → **1.15–1.45** | STA's 10×-attention/3×-e2e is real [X, arXiv:2502.04507] but measured on ~100k-token generation with aesthetic metrics. Our window is only 18.7k tokens (less shrinkable) and the quality bar is *physical consistency for control*, unvalidated [T]. Tile-native mapping to our fabric stands (static masks in the sequencer; GPU STA gets 59% MFU, etched tiles should exceed 90%). |
| B3 | 2:4 structured weight sparsity | **SURVIVES, conditioned** | 1.2–1.4 → **1.2–1.35, requires sparse fine-tuning** | Hardware evidence solid (30–36% perf/W measured [X]). Two honest costs v1 skipped: sparsity metadata adds 2 b per 4 elements → weight stream shrinks to 0.56× not 0.50×; and control-policy accuracy under 2:4 is unmeasured — the model team must fine-tune sparse, not one-shot prune. |
| B4 | Token merging / N_new reduction | **SURVIVES, cautious** | 1.15–1.35 → **1.1–1.3** | ToMe numbers are image-generation; our tokens are already 8×8×4 VAE-compressed, and merge/unmerge error compounds across diffusion steps. Overlaps B2 (both prune attention work) — priced in composition, kept as an independent knob because it also cuts GEMM work. |
| B5 | KV cache FP8→FP4 | **SURVIVES** | **1.03–1.06** | 4-bit KV ≈ lossless is well-replicated in LLMs [X: KIVI lineage]; video-DiT KV quantization exists (QuantCache). Small energy but −26% stream time and half the KV-buffer SRAM. 2-bit (KIVI/LogQuant) stays on the worth-trying list, not the ledger. |
| B6 | FLASH-D / static-max softmax | **SURVIVES, minor** | 1.02–1.05 → **1.01–1.03** | The −20% power is on the attention *unit*, which is ~3% of our die budget — v1 over-credited it. The static-max idea (fixed FP8 scales ⇒ per-layer precomputed max bound, delete the online-max recurrence) survives as our own [T] and is nearly free to try at gate 1. |
| B7 | **Cross-chunk reuse (receding-horizon overlap)** | **UPGRADED — now the flagship** | 1.0–1.5 [T] → **1.3–2.0 (Quality) / 1.0–1.45 certified (Deadline) [X/T]** | v1 called it the most speculative; scrutiny found it's the *best*-anchored: **WorldCache: 2.3× at 99.4% baseline quality on Cosmos-Predict2.5-2B** — an actual video world model [X, arXiv:2603.22286]; **Chorus: 1.45× on 4-step distilled models via inter-request reuse** [X, arXiv:2604.04451] — the same mechanism class, proven exactly where B1 dies. This is also the lever *only* a world-model chip has reason to etch. |

## The B7 determinism resolution (new, important)

Content-aware caching is dynamic — naively it breaks the static-schedule proof. Resolution,
two-tier:
- **Quality mode:** dynamic reuse allowed freely (no hard deadline) — full WorldCache-class
  gains; decisions in the update-engine µcode; features live in the existing DRAM ring.
- **Deadline mode:** the schedule **reserves the worst-case (no-reuse) slot**; dynamic skips
  save *energy and average latency*, never claimed against the worst case — miss-rate proof
  intact. A skip can only count toward the deadline if the reuse floor is **structurally
  guaranteed** — and the founder's train-time real-time chunking is exactly the tool that
  can *train the overlap in* [F], turning a heuristic into a certifiable floor. This
  model-side guarantee is the single highest-value co-design experiment on the list.

## Composition — per mode (v1 composed one number for both modes; that was wrong)

~30% log-space overlap discount applied (all levers harvest world-state smoothness):

| Mode | Live levers | Naive product | **Discounted estimate** |
|---|---|---|---|
| **Quality** (3-step CFG) | B1r·B2·B3·B4·B5·B6·B7 | 2.1× → 6.7× | **≈ 1.7× → 3.8×** |
| **Deadline** (1-step distilled) | B2·B3·B4·B5·B6·B7-certified | 1.6× → 4.0× | **≈ 1.4× → 2.6×** |

## What the stack buys — corrected goals table

| Goal | Status after v2 scrutiny |
|---|---|
| **Relative 2× vs Thor** | unchanged — rides on η ≥ 2.15 solid (Ledger A, 40 W parity). Etch realization edge on B2/B3 (~1.2–1.4× relative [T]) is upside, not headline. |
| **Absolute 5 Hz Deadline Mode** | **v1's "160–250 ms at η=2.79" was WRONG** — it applied B1 and the full stack to a mode where B1 is inapplicable. Corrected (40 W parity): 540 ms ÷ (1.4–2.6) ≈ **208–386 ms at η = 2.15**. 5 Hz closes with **η ≈ 3 AND mid-stack Ledger B** (~185 ms), or a certified-floor B7 at the high end, or further model compression. Honest status: *plausible, not yet on the boundary.* |
| Quality-mode replan | 6.2 s → **≈ 1.6–3.6 s** at η = 2.15 — approaching 0.5 Hz full-quality replanning. |

## Grand total (v2)

| Stack | Multiplier | Status |
|---|---|---|
| Ledger A: architecture η | 2.15 solid / 3.0 target; 1.6–3.2 evidenced | the priced bet [S/X] |
| Ledger B: workload shaping | **1.4–2.6× (Deadline) / 1.7–3.8× (Quality)** | scrutinized, task-gated [X/T] |
| Ledger C: sub-Vmin LVI | 1.5–2.5× | gated side bet [T] |
| **Total vs naive Blackwell execution** | **≈ 4–10× (A×B, mode-dependent; mid ≈ 7×)**, up to ~25× with C | v1 said 7–10×; v2 honesty widens the band downward |

## Worth trying, not yet counted (kept deliberately)

- **B7-dynamic in Deadline mode with a trained reuse floor** — the co-design experiment;
  if train-time chunking certifies ≥30% reuse, Deadline-mode 5 Hz at η ≈ 3 becomes real.
- **Static-max softmax** (ours) — near-free to evaluate at gate 1.
- **2-bit KV** (LogQuant-class) — another ~1.03× and −13% stream if control quality holds.
- **V:N:M sparsity beyond 2:4** [X: up to 2× e2e] — bigger than B3 if the policy tolerates it.
- **Inter-chunk latent warping** (WorldCache's motion-adaptive blending) — pairs with B7;
  could push Quality-mode reuse past 2×.
- **Heterogeneous step allocation** (fewer steps for background tokens [X, arXiv:2605.06892])
  — a B1 substitute that *does* work at few steps by making step count spatially adaptive.

## Non-energy levers (excluded from multipliers, load-bearing anyway)

**Scheduled refresh (spec §4)** — ~0× energy; avoids the 7% nominal / **14–28% hot-head**
opportunistic-refresh bandwidth tax and zeroes refresh jitter by construction (miss-rate
proof prerequisite). Interaction: Ledger B shrinks compute faster than the stream, so the
conveyor approaches binding exactly as these levers mature — scheduling refresh is what
keeps Ledger B's gains from being clawed back. [X: JEDEC + automotive LPDDR5 practice; S/T]

## Verification hooks (all pre-silicon)

1. Every surviving lever is Tier-1-simulable as a `WorkloadParams` sweep — no core edits.
2. B2/B4/B7 quality costs measurable on the local RTX proxy with task metrics.
3. Gate-1 addendum: µcode/sequencer budget for static masks, merge permutations, reuse
   thresholds (≪1% die [T]); B7's worst-case-slot scheduling folds into the existing
   deadline analysis.

---

## Ledger D — architecture-agnostic η levers (research 2026-08-04)

Three parallel literature reviews on raising η **without betting on a model shape**.
Verification status is marked per item, per lesson L10: a delegated finding is a claim
until someone opens the source.

### D1. Alternative number systems — BRANCH CLOSED

| Technique | Verdict | Evidence | Verified |
|---|---|---|---|
| Logarithmic number systems | **worse than INT8** | 7 nm ASAP7, registers counted: Kulisch LNS 190.3 fJ vs INT8 160.2 fJ PDP, 19 % worse. Published wins approximate the accumulate, costing LLaMA-3.1-8B 6.24 → 8.33 ppl | **yes** — figures confirmed in extracted PDF text |
| L-Mul | **~0 on an ASIC** | 95 % (analytic, vs FP32) → 42 % multiplier-only on FPGA → 14.6 % system → 0, since the win is deleting 1,156 hardened DSP slices | **yes** — figures confirmed in extracted PDF text |
| Posits | **cost more** | 1.32x area, 1.38x power at matched width; MX gets the taper with a static layout | no |
| AdderNet / ShiftAdd / BitNet | **disqualified** | require training from scratch, or land on the prohibited quantization axis | no |

### D2. INT vs FP datapath — the one candidate worth an afternoon

INT8 with a fixed-point accumulator is reported as the efficiency floor, FP8-E4 costing
+53 % gates (corroborated ~40 % by synthesis) [X: arXiv:2303.17951]. **Not verified here.**
It matters because self-attention runs FP8 and is **73.3 % of our arithmetic energy** [S],
so this lever lands on the dominant term. Verify the source before pricing it.

### D3. Compute-in-memory — REJECTED, but not for the reason we were going to give

Do **not** reject CIM on weight residency. At AI ≈ 16,000 FLOP/byte we have thousands-fold
reuse per load, so reload energy is negligible and that argument would be refuted. Reject
on **density and utilization**: TSMC 3 nm DCIM at 3.78 Mb/mm² against ~30 Mb/mm² for plain
SRAM turns our 90 MB into ~190 mm². [X, unverified.]

**House rule: never cite a CIM macro TOPS/W.** Macro headlines span 89-4094; system-level
results cluster at 23-37 across nodes. That macro-to-chip collapse is the same error shape
as our own 29-55x ledger artifact: a subtotal quoted as a total.

### D4. Power-of-two weights — a QUALITY lever, not an energy lever

PoTPTQ matches or beats GPTQ/AWQ at 3-bit, and LRQ-DiT targets text-to-video diffusion
transformers, our exact model class [X, unverified]. But a PoT weight turns a 4x4
multiplier into a shifter, and that multiplier is only 11-17 % of MAC energy. Put log-coded
weights on the **decode path** out of SRAM, not in the arithmetic. It may let us hold a
bit-width we would otherwise concede, which is the only way this literature helps the
no-aggressive-quantization constraint.

### The convergent finding, which matters more than any single lever

Three streams reasoning from different literatures, plus our own computation, agree:
**the multiplier is 11-17 % of MAC energy, and ~85 % of chip energy is operand delivery,
accumulation, clock, leakage and control.** Our own number: the accumulator alone is 56 %
of arithmetic energy [S, computed here].

Consequence: **η does not come from better arithmetic.** Multiply-side techniques are
capped near 1.07x whatever a paper claims, and the whole numerics domain is worth
~1.05-1.16x against a required 2.15. The remaining levers are all inside that 85 %:
accumulator amortization (2.1x on arithmetic energy, computed and verified here),
operand delivery, clock and leakage.

### D5. Circuit and physical-design levers — the clock is the floor

**Measured, and it reframes the problem.** Eyeriss (TSMC 65 nm, fabricated) [M, quotes
verified in extracted text]: **clock network 33-45 % of power, multiplier+adder 3-9 %**,
scratchpads 33-42 %. Verbatim: *"the ALUs only account for less than 10 % of the total
power"* and *"Besides the clock network, the spads dominate."* Eyeriss v2: the clock share
**triples from ~20 % to ~55 % as effective utilization falls** — and batch-1 attention is
exactly that regime. Corroborated by Simba (16 nm, measured: MACs 11.2 % of PE area) and
Hameed (90 % overhead / 10 % functional units).

**Consequence for our fabric [T, load-bearing].** At ~1.9 M MACs and 1.05 GHz against a
~19 W fabric budget, a conventionally pipelined flop-per-MAC array clocks 40 bits/MAC and
lands at **32-120 W — it does not fit at all**. An 8-wide adder tree takes it to 7 bits/MAC
and 5.6-21 W. **The adder tree is therefore a feasibility decision, not an optimization**,
and flop clock-pin plus local-tree energy in the target PDK is the single most important
Tier-2 characterization.

Shipped precedent [M]: TPUv4i replaced 128 serial two-input adders with four-input sums,
saving **40 % area, 25 % power, and 12 % of MXU peak power**.

**Ranked survivors** (full 24-item table in the research transcript): 1) adder-tree
register amortization; 2) latch-based design with time borrowing, converting ~25 % frequency
headroom into lower Vdd at fixed throughput — the one candidate that attacks the P6 DVFS
wall with no model-side change; 3) pulsed latches, derated to 10-18 %; 4) schedule-driven
spatial PE gating (our static schedule gives zero prediction error, and DiT head dims are
ragged against a 128-wide array); 5) GALS pausible clocking [M, NVIDIA 16 nm]; 6) multi-Vt
and body bias.

**Rejected with evidence:** LC resonant clocking (needs ~23x the inductance at 1.05 GHz and
**detunes under clock gating**, which is our main lever); low-swing clocking (5.8 % of total
measured on a fabricated 90 nm MAC test chip, and no swing headroom at 0.7 V); clock mesh
(surge current, and we do not need 20 ps skew at a 1 ns period).

**Three families closed with primary sources — do not spend another research run on them.**
*Adiabatic and charge-recovery logic* was refuted head-to-head in 1994: *"In almost all cases,
voltage scaled CMOS dissipates less power for the same level of performance."* Every measured
win is slow and old, the power-clock generator costs +52 % when it is counted at all, and a
10x energy win needs ~20x ramp stretch for ~160x throughput loss per unit hardware. It also
scales **backwards** against the node, because its floor is leakage-limited. *Full asynchronous
/ QDI* costs **70-100 % area** by its proponents' own words, and dual-rail forces activity
factor 1.0 per bit on ~2x wire capacitance against a real 0.1-0.25 — a 4-10x datapath penalty
before completion detection, with the async community's own tools paper calling the EDA
landscape *"bleak"* and sub-10 nm *"future work."* *Wave pipelining* has a delay-balance floor
of ±20 %, which is smaller than 4 nm variation alone, and no published energy story at all.

**Two widely-cited numbers that do not survive checking**, recorded so we never repeat them:
AMD Piledriver's resonant clocking is **4.5 % of core power** in the peer-reviewed paper, not
the "10 % of total IC power" that circulates from the press release; and Eyeriss's famous 45 %
zero-gating saving is measured against an *ungated* baseline on ReLU CNNs.

**One rejection matters for integrity:** zero-operand gating. Eyeriss's famous 45 % is
measured against an *ungated* baseline on ReLU CNNs with 77.6 % zeros. Transformers have
essentially no exact zeros. **Citing that number for our accelerator would credit the
design under test with sparsity the workload does not have, breaking the one-utilization-
model invariant.** Honestly-baselined value at our zero rates: ~2-3 % of dynamic power for
5.7 % area. Reject.

**The sobering finding.** Eyeriss achieves 3-9 % of energy in functional units; Hameed's
ladder tops out near 35 % for fused custom datapaths. **Our gate criterion of FU fraction
>= 35 % is more ambitious than any purpose-built DNN ASIC has published**, and clocking
plus sequencing is the largest single bucket standing between us and it.

**Net:** everything below rank 1 composes to roughly **10-20 % of chip power**. Real, worth
taking, and not a factor of two. Rank 1 is different in kind.

### D6. The voltage and margin stream — and a framing correction that changes the composite

**The correction, which matters more than any technique in this ledger.** `eta = f_ours/f_gpu`
is the wrong model for circuit-level work. That identity captures *architectural* overhead
removal: instruction fetch, register file, cache hierarchy, dynamic scheduling. Almost no
circuit technique changes `f` at all — voltage scaling cuts multiplier energy and SRAM energy
and clock energy by the same V², leaving the *fraction* identical while improving J/op.
**Circuit gains are a separate multiplicative ledger on top of eta, not a component of it.**
Ledger A and Ledger C were already structured this way; this confirms the separation was
right, and it means the two must be composed rather than treated as overlapping.

**A bound on eta derived from our own fixtures — CORRECTED 2026-08-04, and then MEASURED.**
The research agent's version of this table divided chunk energy by a FLOP count that
double-counted forward passes, producing 0.78 pJ/FLOP and implying the workload ran at
768 TFLOP/s — above this board's dense-GEMM ceiling. A workload cannot be more efficient
than a pure GEMM on the same silicon; that impossibility is what exposed the error. I had
already committed the wrong figure before catching it. Correct values, regenerated from
`forward_per_step(wp).flops * wp.diffusion_steps`:

| Anchor | model FLOPs | energy | implied TFLOP/s | pJ/FLOP |
|---|---|---|---|---|
| 3step_cfg_n3120 | 7.11e14 | 1110 J | 384 | **1.562** |
| 2step_cfg_n3120 | 4.74e14 | 749 J | 380 | 1.580 |
| 3step_cfg_n1560 | 3.59e14 | 591 J | 364 | 1.648 |
| 1step_batch1_n3120 | 1.18e14 | 193 J | 366 | 1.631 |

**We then measured the arithmetic ceiling on the same board rather than estimating it**
(`scripts/measure_fu_fraction.py`, fixture `rtx_pro_6000_fu_fraction.json`). An
L2-resident dense GEMM is the most arithmetic-dense thing this silicon can run, so its
energy per FLOP bounds multiplier energy from above:

| | best measured | at |
|---|---|---|
| BF16, same precision as the anchors | **1.480 pJ/FLOP** raw, 1.298 marginal | n=4096, 405 TFLOP/s |
| FP8 E4M3 | **1.192 pJ/FLOP** raw, 1.039 marginal | n=8192, 504 TFLOP/s |
| Idle floor, clocks up | 73.7 W | — |
| **f_gpu ceiling** | **<= 72-76 % raw, 63-67 % marginal** | one-sided |

**Read the f_gpu bound honestly: it is weak and it is not the interesting result.** A GEMM
still pays for register files, L2, warp scheduling, clock and leakage, so bounding the
multiplier share by a GEMM's total energy cannot be tight. What the measurement actually
settles is more useful, and it is unfavourable:

**The workload runs at 1.562 pJ/FLOP against a same-precision dense-GEMM best of 1.480 —
about 95 % of peak GEMM efficiency.** The GPU is *not* squandering most of its energy on
workload-specific overhead. There is roughly 5 % of that kind of waste to reclaim, not the
large "general-purpose tax on our particular workload" the eta story is sometimes told
with. **Eta cannot come from the GPU running our workload badly, because it does not.** It
must come from the architectural overhead present even in the GPU's best case — register
files, cache hierarchy, clock distribution — which is precisely what Eyeriss (multipliers
3-9 % of power) and Hameed (10 % to functional units) describe. The thesis survives; one
convenient way of telling it does not.

**Two further measured findings.**

*bw_util is identified, and the fitted value is refuted.* The calibration pinned `bw_util`
at 1.0000 against its box bound and `rpu/report.py` correctly reported it UNIDENTIFIED.
A pure DRAM stream achieves **1461-1464 GB/s, or 81.5-81.7 % of the 1792 GB/s spec** — and
since a contiguous copy is the best case for bandwidth, that is an *upper* bound on what a
real scattered workload sees. The fit's 1.0000 is not attainable. Deliberately not folded
back into the solver: this is a cross-check that shares no assumptions with the
least-squares fit (lesson L5), and it is worth more as an independent check than as another
fitted point. Refitting is a separate, explicit decision.

*The baseline is itself energy-bound, measured.* Board power sat at **600.0 W in every
single arithmetic configuration** — a hard cap, never a compute ceiling. FP8 buys only
1.24x over BF16 here (1.480 -> 1.192 pJ/FLOP) rather than the nominal 2x, because the part
is clamped by watts and not by multipliers. That is the project's own energy-rate-bound
thesis appearing on the baseline hardware, and it is the cleanest confirmation of it we
have. Note it differs from the 1.77x FP16->FP8 figure from the DVFS sweep; the two use
different methods and the gap is not yet explained.

**Sub-Vmin, resized: 1.4-1.7x on logic, 1.15-1.25x at system level.** Full argument and the
leakage sign-flip table now live in [`CHIP_SPEC.md`](CHIP_SPEC.md) §6b. **Ledger C is
downgraded from 1.5-2.5x on everything to ~1.5x on the logic term**, because LPDDR5X and its
PHY run at a fixed rail and cannot be voltage-scaled at all.

**New entry — droop-aware static scheduling, 6-10 % of logic power (~1.5-2.5 W), and the one
genuine differentiator in this domain.** Measured guardband on shipping silicon is **9-18 %
program-dependent on a GTX 680 and ~20 % across four Fermi/Kepler parts**; decomposing the
0.1 V Vmin spread across 57 programs at fixed temperature gives **voltage noise 0.10 V,
process 0.07 V, temperature 0.02 V**, and within voltage noise it is **di/dt droop, not IR
drop**, that dominates [X*]. Every published mitigation predicts droop from performance
counters and pays a misprediction margin. **A fully static schedule removes the predictor and
its margin**: worst-case dI/dt is characterizable at compile time because nothing else can
run, and tile activation ramps can be shaped offline in the µcode toolchain (§6d). The physics
favors this over the obvious alternative: since ΔV is proportional to ΔI·sqrt(L/C), halving
droop with decap needs **4x the decap**, while attacking ΔI with the schedule is **linear**.

**Two conditions on that lever, both binding.** The kill risk: one survey finds that on large
multicore parts the droops are so severe that Vmin becomes *virtually workload-independent*,
leaving no program-dependent headroom to reclaim. If a 256x256 array behaves that way the
lever collapses, so it is a Monte Carlo input, not an assumption. The fairness risk: crediting
us with a smaller guardband because we are statically scheduled gives the design under test
something Thor and B200 do not get. It is defensible, since they genuinely carry runtime
predictor margin — but **it must be a separately labeled bet with its own band, exactly like
eta, and never a term in the shared utilization model.**

**Backside power delivery — escalate as a node decision, not a circuit decision.** Intel
PowerVia measured on an Intel 4 test chip: **>30 % IR-droop reduction and 6-6.7 % Fmax**.
TSMC A16 Super Power Rail claims **15-20 % lower power at iso-speed**. This is the largest
single number in the domain and **it does not exist at N4 or N5** (nor at N2/N2P, which are
frontside). Available on Intel 18A now and TSMC A16 in 2026-27. Thermal caveat specific to
us: backside power moves transistors away from the heat-extraction path, and we are fanless.

**Rejected, with the reason stated once so nobody reopens them:** Razor-class timing
speculation (see §6b — it is energy-negative per inference, chip-to-chip Vmin spread exceeds
the exploitable window, and replay means variable latency against a hard deadline); voltage
stacking (unmitigated imbalance drove a measured 230 mV guardband on a 900 mV rail, four times
the delivery loss it recovers; worst-case-reliable sizing needs 912 mm² of regulator);
integrated voltage regulators as an efficiency play (90 % measured against 90-93 % for a good
off-chip buck, and Intel shipped, removed, then reshipped it); FD-SOI and body biasing (no
5 nm FD-SOI exists, and bulk FinFET has no body contact); deep-trench decap.

**Write the power-delivery ceiling into the spec so nobody spends a quarter on it:** on-die
plus package I²R loss as a percentage *equals* the IR-drop margin budgeted. At 40 W that is
~4-6 W, so perfect, free, zero-area delivery buys ~12 %, and best-in-class over standard
practice buys 4-6 %.

**Composite.** Ledger C at ~1.2x system level, times the architectural eta, is how the
program reaches its bar. Sub-Vmin is a **contributor to eta* ~= 2.8, not a solution to it**,
and the honest headline stays architecture-first.

*Provenance note: [X*] marks claims reported by the research agents with primary sources in
the session scratchpad that I did not personally open. The Eyeriss and Leng material was spot
-verified against extracted text; the Zimmer 3.3x and the Razor energy-negative result were
not. Per lesson L10, they are labeled rather than promoted.*

