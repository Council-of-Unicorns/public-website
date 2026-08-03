# FM-RPU Concept-Proving Simulator — System Design

**Target being proven:** a head-resident accelerator that runs a DreamZero-style 14B video-action world model at **5 Hz control**, **2 s prediction horizon**, at **40 W head power — scored at power parity with Thor-in-head** — beating Jetson Thor and removing the datacenter-B200 dependency.

This document specifies two simulators:

- **Simulator A** — specialized for the DreamZero family (the concept proof).
- **Simulator B** — dual-target (DreamZero + JEPA), as an industry-pivot hedge.

B is defined as a set of deltas on A, because the honest engineering claim — that generality is nearly free — only holds if the two share almost all of their structure. Part C answers whether B keeps most of A's gains, and states the single condition under which it would not.

---

## 0. Proof standard

A simulator that predicts a chip that does not yet exist earns trust only by first reproducing hardware that does. The instrument is therefore built **measurement-first**:

1. It must reproduce your measured B200 runs of your 3-step DreamZero fork (latency, energy) to within a stated tolerance (target < 15% on latency and energy) **before** any extrapolation is trusted.
2. It must reproduce at least one Thor or Orin data point and DreamZero's public anchors (naive ~5.7 s/chunk at 16 steps; ~7 Hz optimized) within the same tolerance.
3. Feasibility is reported as a **region with confidence bands** over the uncertain inputs, never a single point estimate.
4. Every hardware row is evaluated under **identical utilization assumptions**; the specialized chip is never granted ideal utilization while baselines get realized numbers.

The output that matters is not "the chip is X TOPS." It is: *does a manufacturable (bandwidth, compute, SRAM, watts) point clear the 200 ms deadline at ≤ 40 W for this workload, and where does Thor fall short.*

---

# PART A — Specialized simulator (DreamZero-optimized)

The simulator is five coupled models over a shared parameter store. Fidelity escalates in tiers (§A7); this document specifies Tier 1 (analytical roofline + memory-traffic), which produces the feasibility region and screens the design space.

## A1. Workload model — the DreamZero fork as parameters

Nothing about the model is hardcoded; the architecture is a swept input so the proof survives a model revision.

**Backbone (defaults from Wan2.1-I2V-14B):**

| Param | Default | Note |
|---|---|---|
| Params `P` | 14e9 | monolithic DiT |
| Hidden `d` | 5120 | |
| Layers `L` | 40 | |
| FFN dim | 13824 | |
| Heads | 40 | |
| Weight precision | 4-bit | mixed: FP8 on QKV/softmax, FP16 accum |

**Horizon / tokenization (drives everything downstream):**

| Param | Default | Note |
|---|---|---|
| Resolution | 480×832 | |
| VAE spatial / DiT patch | 8× / 2×2 | → 30×52 = **1560 tokens/frame** |
| VAE temporal | 4× | |
| Prediction rate | ~6 latent fps | swept |
| Horizon | **2.0 s** | → ~12 latent frames of context |
| KV context `N_ctx` | ~18.7k tokens | 12 × 1560; the 2 s rolling window |
| New-chunk tokens `N_new` | ~1.5–3.1k | tokens re-diffused per control step (receding horizon) |
| Action tokens | ~64 | |
| Task/text tokens (cross-attn KV) | ~256 | |

**Critical modeling note — the video branch still runs even with no pixel output.** Your fork drops the *pixel decoder* (no reconstruction), but DreamZero's own finding is that removing video *generation* barely helps at 14B because the DiT block count × step count dominates. So `N` includes the video-latent tokens; the simulator processes them through the DiT and simply skips the VAE decode operator. Do not model "no pixels" as "no video cost." *(Source of this cost claim — on which the video-without-pixels modeling property rests: DreamZero, "World Action Models are Zero-shot Policies," arXiv:2602.15922. Cite the exact section in the calibration anchor provenance; the naive ~5.7 s/chunk @ 16 steps and ~7 Hz optimized anchors come from the same paper.)*

**Diffusion / control schedule:**

| Param | Default | Note |
|---|---|---|
| Diffusion steps | **3** | your measured result; swept 1–16 |
| Guidance | CFG pair (or distilled batch-1) | weight-shared |
| Control period | **200 ms** (5 Hz) | hard deadline |
| p99.9 latency target | ≤ ~160 ms | leaves margin for motor handoff + jitter |
| Motor controller | 500–1000 Hz, separate island | not simulated here except as a deadline consumer |

**Per-operator output.** For each operator — VAE encode, patch embed, and per layer {QKV proj, self-attn, out proj, cross-attn, FFN}, then flow update and action head — the workload model emits a tensor of `(FLOPs, weight_bytes, activation_bytes, KV_bytes)`. This per-operator granularity is the whole point: the bottleneck migrates between operators as the horizon and step count change, and an aggregate FLOP count hides exactly that.

## A2. Compute + memory-traffic model (roofline core)

Per operator, per diffusion step:

- `FLOPs_matmul = 2 · P_active · N_new` (weight-bound linear layers)
- `FLOPs_attn  = 4 · L · N_new · N_ctx · d` (queries = new chunk, keys/values = full 2 s window)
- `bytes_weight = P_active · w_bytes` **fetched once per step, reused across the CFG pair** (weight-stationary sharing modeled explicitly)
- `bytes_KV = 2 · N_ctx · L · d · a_bytes` **fetched once per step and reused across the CFG pair, symmetrically with the weights** — the context KV is identical for both CFG branches, so do NOT re-read it per forward pass or you double-count ~7.6 GB/step (~+50% on the binding bandwidth term). At a 2 s (~18.7k-token) horizon this term ≈ the weight traffic (≈ 7 GB), a first-class cost, not a rounding error. (In the distilled batch-1 path there is no CFG pair to share across.)
- `bytes_act` ≈ tiled activation traffic (mostly SRAM-resident; small if fused)

Arithmetic intensity per operator places it on the roofline for each hardware row → **compute-bound vs bandwidth-bound classification is an output, not an assumption.** This is the single most important thing the specialized simulator computes, because it decides how to provision the chip:

- **Short horizon / few tokens / low batch → weight-bandwidth-bound** (re-streaming 7 GB every step with little reuse).
- **Long horizon (your 2 s) → KV-bandwidth grows and matmul+attention compute grows**, and the operating point can cross into **compute-bound or KV-bound**. The simulator must find that crossover; provisioning follows it.

**Weight-residency check.** If chip SRAM ≥ working set, weights stream from HBM once per chunk and amortize across steps; else once per step. For 14B @ 4-bit = **7 GB**, no head-power chip holds weights in SRAM, so the model correctly predicts HBM weight-streaming every step. (This fact also drives Part C.)

## A3. Hardware model

Each hardware row is `{peak FLOPS per precision, HBM BW, HBM capacity, SRAM capacity, SRAM BW, dequant throughput, attention-engine throughput, interconnect BW, fixed per-op overhead, TDP}`.

| Row | FP4 peak | Mem BW | Capacity | Power | Role |
|---|---|---|---|---|---|
| Jetson Thor | 2.07 PF | 273 GB/s LPDDR5X | 128 GB | 40–130 W | incumbent to beat |
| B200 | ~9 PF (dense FP4) | ~8 TB/s HBM3e | 192 GB | ~1000 W | calibration + "what you're replacing" |
| **FM-RPU-14** | swept | swept (HBM) | ~16–32 GB | 40 W (= Thor-in-head) | design under test |

FM-RPU is a **parameter sweep**, not a point, so the output is a design frontier. Utilization factors (compute, BW) are applied identically to all rows.

## A4. Latency model

Full sensor-to-action loop, per stage `t = max(compute_time, mem_time) + fixed_overhead`, with a configurable compute/memory overlap factor:

```
capture → ISP → VAE encode → PREFILL/attend context
        → [ 3 × ( paired-CFG DiT forward over N_new, attending N_ctx KV ) → flow update ]
        → action head → EMIT chunk → motor island
```

Report **p50 and p99.9**, and a **deadline-miss-rate** against the 200 ms period under a jitter model. Framing matters: a missed control deadline is a stability/safety event, not a dropped frame, so the target is a miss-rate (e.g., < 10⁻⁴), not a mean.

## A5. Power / energy / thermal model

- `Energy = Σ FLOPs · e_flop(precision) + Σ bytes · e_byte(tier) + static_fraction · TDP · t` — the last term is static/leakage power integrated over the chunk time (one shared `static_fraction`, every row's own TDP; it is the Part-C.3 "idle silicon leaks" term that prices the union design's over-provisioning, and it is included in the calibration target because measured *board* energy includes it). **Whether HBM byte energy dominates is a computed *output*, not an assumption** (emit the byte-vs-FLOP energy split alongside the roofline regime; assert it, don't hardcode it). `e_byte` is the constant that must be calibrated against measured board power.
  - **Units discipline (an 8× landmine):** store `e_byte` in **pJ/byte** and `e_flop` per-op; published DRAM figures are usually pJ/**bit** (multiply by 8). Add a unit-consistency test.
  - **Defaults, HBM3e-era (B200-class), used only until calibration overrides them:** HBM3e ≈ 2.5 pJ/bit ≈ **~20 pJ/byte** (range ~15–25); SRAM ≈ 0.1 pJ/bit ≈ **~0.8 pJ/byte**. The older "30–40 pJ/byte" figure is HBM2-era and ~1.5–2× high. Note these literature values are DRAM-**IO** energy only; board-measured byte energy (controller + PHY + on-die movement) is higher, which is exactly why `e_byte` is calibrated, not trusted from a datasheet.
- Outputs: avg power → battery draw; peak power; energy/chunk.
- **Thermal transport sub-model (part of the proof, not an afterthought):** junction → vapor chamber → neck heat-pipe/liquid conductance → torso radiator, solved for steady-state ΔT. The head is effectively **fanless** (NEO-class acoustic ceiling ~22 dB), so the binding constraint may be *heat rejection through the neck*, not the battery. The simulator reports the sustained-power ceiling the neck path can carry and flags if the compute point exceeds it.

## A6. Calibration & validation protocol

1. **Anchor reproduction** — model your B200 fork runs, a Thor/Orin point, and DreamZero's public anchors; report modeled-vs-measured error; extrapolate only inside the calibrated envelope.
2. **Fairness** — one utilization model for all rows; derive it from measurement.
3. **Adversarial baseline** — a red-team gives Thor its best case (max distillation onto Thor, best batching) and B200 its best case; the specialized chip must still win.
4. **Monte Carlo** over the load-bearing uncertain inputs — realized BW utilization, `e_byte`, tokens/frame, and the distillation/step ceiling — producing a feasibility frontier with confidence bands and a **sensitivity ranking**. Expect the conclusion to hinge on two numbers: realized memory-bandwidth utilization and how far step/horizon compression can go before task success degrades.

## A7. Fidelity tiers (escalate only survivors)

| Tier | Tool class | Buys you |
|---|---|---|
| T1 | analytical roofline + traffic (this doc) | feasibility region, design-space screen |
| T2 | dataflow/mapping (Timeloop + Accelergy class) | trustworthy energy from real tiling/reuse |
| T3 | cycle-approximate (systolic-array model + DRAM sim, e.g. SCALE-Sim + Ramulator class) | scheduling, bank conflicts, interconnect don't erase the roofline |
| T4 | RTL + gate-level power/area | tapeout signoff |

Promote a design point up a tier only while it is still winning; kill it cheaply at T1 otherwise.

*Tooling note:* **SCALE-Sim v3** now bundles Accelergy (energy) and **Ramulator** (a cycle-accurate DRAM *timing* simulator, validated against DDR RTL), so the T2/T3 split partly merges in one toolchain — plan the harness around SCALE-Sim v3 + Accelergy + Ramulator rather than three separate integrations. (Ramulator models DRAM timing, not area; area/energy come from Accelergy.)

## A8a. Success metric — speedup vs the incumbent (2× = success)

The project's success criterion is **≥ 2× inference speedup over Jetson Thor** on the identical
world-model workload. This section defines the metric so it cannot be gamed:

- **Speedup** `S = t_chunk(Thor) / t_chunk(FM-RPU)`, same `WorkloadParams`, same shared
  `UtilizationModel` (P1). Reported as a **region** (P7): a Monte-Carlo distribution over the
  load-bearing uncertain inputs, with `P(S ≥ 2)` and quantiles — never a scalar.
- **Power-capped chunk time.** A chip cannot sustain throughput whose energy exceeds its power
  budget, so `t_chunk = max(t_roofline, E_dynamic / (TDP · (1 − static_fraction)))` — applied
  **identically to both rows** (P1). This term is what makes the metric honest: with identical
  per-FLOP energy, two power-limited chips satisfy `S = TDP_dut / TDP_baseline` as an identity,
  at power parity the TDP ratio cancels and **S = η exactly**: a part with η = 1 ties Thor, and every win is pure efficiency advantage.
- **Two baseline bases, both reported:** (a) *Thor-in-the-head* — TDP capped at the neck-path
  sustained ceiling (~40 W, from A5's thermal model), the deployment-honest primary basis; and
  (b) *Thor-unconstrained* (130 W) — the A6.3 adversarial basis. Success claims cite (a) and
  must survive (b) being shown alongside.
- **Etch-efficiency advantage `η`** (FM-RPU per-FLOP energy = shared `e_flop / η`) is the D7
  case in energy form: a specialized dataflow part may genuinely beat a GPU's pJ/FLOP, but at
  Tier 1 the headline stays `η = 1` (P1-fair). The simulator emits (i) the headline region at
  `η = 1`, (ii) the **required η\*** for median `S = 2` on each basis — the number the chip
  architecture must deliver — and (iii) a clearly-labeled scenario band under a stated η prior.
  η is never silently folded into the headline.
- **FP16→FP4 energy-scaling `s`** is a Monte-Carlo input (prior ~U(4, 16)); the measured anchor
  pins `e_flop` at FP16, and the 4-bit workload rides `e_flop_fp4 = e_flop_fp16 / s` until an
  FP8/FP4 anchor pins it. Applied to both rows identically.
- **P6 applies:** an FM-RPU speedup region is emitted only under a passing calibration.
- **Solid-beat criterion (2026-07-28, supersedes the bare bar as the design target).**
  (2026-07-29: FM-RPU is scored at 40 W, power parity with Thor-in-head, so S = η and
  the old 0.75 power handicap is gone.) "Beats Thor" is scored three ways, in increasing
  strictness: (i) *bare*: median S ≥ 2 in the best mode → η ≥ 2.05; (ii) **solid (the
  success criterion): S at the 5th percentile ≥ 2 in EVERY operating mode, including
  Deadline** → η ≥ 2.15; (iii) *solid-with-margin* (the design target): solid holds even
  granting Thor a 25% better thermal budget (50 W in-head) → **η ≥ 2.80, rounded to a
  design target of η = 3**. The margin covers the least-anchored inputs: the neck-ceiling
  estimate, Thor's realized efficiency, and the memory-regime uncertainty. Consequence of
  parity scoring: the solid bar (2.15) sits mid-band in the architecture-only evidence
  (1.6–3.2×) and the design target (3.0) at its top — the stacked levers (D7
  realized-utilization edge, Ledger-B realization gains, sub-Vmin) are margin again, not
  load-bearing. It also aligns the solid bar with the Tier-2 kill criterion (η ≥ 2.2).

## A8. What Simulator A proves

- A **feasibility map** over (horizon, steps, tokens, precision, chip params): does the point clear 200 ms at ≤ 40 W with an acceptable deadline-miss-rate.
- The **bandwidth-vs-compute crossover** for 5 Hz @ 2 s — the number that sets provisioning.
- The **minimum viable spec**: the (HBM GB/s, FP4 TFLOPS, SRAM MB, W) frontier that clears the deadline; where Thor's 273 GB/s wall falls; and the speedup/energy ratio vs a B200 held to head power.

---

# PART B — Dual-target simulator (DreamZero + JEPA)

B reuses A's five models verbatim and adds a second **workload generator** plus two small abstractions. Nothing in the roofline, hardware, latency, thermal, or calibration layers changes. That reuse *is* the hedge: if B required rebuilding those layers, the chip couldn't be general either.

## B1. The etch line (what is shared vs what diverges)

Both families reduce to the same primitive: **iterated transformer inference over a mutable latent state, weights reused across an iteration axis, under a deadline.** The simulator encodes this as one abstraction with a swappable axis:

| | DreamZero | JEPA-MPC |
|---|---|---|
| Front-end | VAE latent encode | frozen ViT encode (**once per obs**) |
| Core | 14B DiT forward | predictor forward (same math class) |
| Iteration axis | **3 steps × CFG pair** (sequential) | **M candidates × H horizon** (parallel) |
| Inter-iteration update | flow/ODE step | CEM/MPC refit (sample→score→resample) |
| Guidance | CFG (or distilled) | none |
| Pixel decode | none (your fork) | none |
| State | grounded + speculative KV | grounded + candidate-rollout KV |

Everything above the "iteration axis" and "inter-iteration update" rows is byte-for-byte identical hardware. Only those two rows differ, and both touch **only latent state (KB–MB), never the weight-bandwidth hot path.**

## B2. Deltas added to each model layer

- **Workload model:** add a JEPA generator — encoder-once token cost + predictor rollout tokens; the batch axis is now `M` candidates; horizon `H`. Reuse the identical per-operator `(FLOPs, weight_bytes, act_bytes, KV_bytes)` emitter.
- **Roofline:** parameterize the **reuse-axis width**. Diffusion at control rate is low-batch (CFG pair ≈ 2) → little weight amortization → **bandwidth-bound**. JEPA-MPC is high-batch (hundreds of candidates) → heavy weight amortization → **compute-bound**. Same equations, opposite regimes.
- **Hardware:** add a small **programmable-update-engine** cost (a microcoded vector-reduction unit that runs flow-ODE *or* CEM); model its area/energy as a few percent of the matmul/attention datapath.
- **Latency:** swap the inner loop (sequential K-step denoise ↔ parallel M-candidate rollout + CEM refit); the deadline/thermal machinery is unchanged.
- **Provisioning tension (the one real cost):** the chip must satisfy the **union** of both families' demands — the **bandwidth floor** set by low-batch diffusion **and** the **compute headroom** set by the MPC batch. The simulator's job in B is to find a single point that clears 5 Hz @ 2 s in **both** modes.

## B3. What Simulator B proves

- A single manufacturable (HBM GB/s, FP4 TFLOPS, SRAM MB, W) point that clears the deadline for **3-step DreamZero** *and* **M-sample JEPA-MPC**.
- The **perf/watt delta vs Simulator A's specialized point on the DreamZero workload** — the measured "cost of generality," which is the input to Part C.

---

# PART C — Does the dual-target design keep most of the specialized gains?

**Short answer: yes — expect B within single-digit percent of A's perf/watt on DreamZero — with exactly one condition that would break it, which for a 14B model does not hold.**

The reasoning, and why it's a *checkable* claim rather than a hope:

**1. The shared, etched substrate is where the cost lives.** Weight delivery (4-bit dequant + weight-stationary tiling), attention, matmul/FFN, and the mutable-state cache account for essentially all of the energy and area and virtually all of the HBM traffic. Both designs run this bulk identically. The transformer forward passes are ~99% of the FLOPs and ~100% of the weight bandwidth.

**2. The divergent part is off the hot path.** The inter-iteration update (flow vs CEM) and the guidance handling (CFG pair vs candidate batch) touch only latent state — kilobytes to a few megabytes — and never re-fetch weights. Making that unit programmable rather than fixed-function costs on the order of **1–3%** of datapath efficiency, not a factor of two. This is the direct payoff of etching the *invariant* and leaving the *variant* microcoded.

**3. The true cost of generality is over-provisioning the non-binding resource, not a per-workload efficiency hit.** Because diffusion is bandwidth-bound and MPC is compute-bound, the union point carries some compute that diffusion doesn't use and some bandwidth that high-batch MPC doesn't use. That shows up mostly as **static/leakage power on idle silicon in each mode** — a few watts — not as slower execution of the workload actually running. On the DreamZero workload specifically, B runs the same hot path as A and pays only (2) plus the leakage of A-plus-extra-compute-for-MPC.

**4. The one condition under which B would *not* keep most gains — and why it fails here.** If the specialization would have **collapsed a memory-hierarchy tier** — e.g., if a DreamZero-only chip could keep the *entire working set SRAM-resident and drop HBM altogether*, while JEPA's larger batch/working set forces HBM back in — then B would carry a whole memory tier that A shed, and the gap would be large (memory-system-level, not update-level). **This is the thing to check in the simulator.** For a 14B model at 4-bit, the weights are **7 GB**, which does not fit in any head-power SRAM under either family. Both families therefore stream weights from HBM every step; the tier structure is identical; and the specialization has no memory tier to collapse. The condition fails, so generality stays nearly free.

**Where B would start to cost real gains:** only if the deployed control model shrinks enough that its working set becomes SRAM-resident (roughly ≤ a couple of GB, i.e. a ~1–3B model at 4-bit). At that size a DreamZero-only design could go HBM-less and pull far ahead — but that same shrink also undermines the "you need custom silicon at all" premise, because a 1–3B model starts to fit Thor. In other words, the regime where specialization decisively beats generalization is largely the regime where **neither** chip is needed. That is a reassuring place for the dual-target bet to sit.

**Unstated assumption to make explicit — JEPA predictor size is a swept input, not 14B.** The argument above (and the B1 "same 14B DiT core" row) implicitly runs JEPA on the 14B core. Empirically, JEPA world models are **1–2B today** (V-JEPA 2 is 1.2B; DINO-WM is smaller), not 14B. This does not by itself break the *DreamZero-side* claim — on the DreamZero workload B still runs the identical 14B HBM hot path as A — but it changes the two numbers that set the *cost of generality*: (1) the **union compute headroom** is `(JEPA params × MPC batch × horizon)`, which at 1–2B × hundreds-of-candidates is the same order as the 14B diffusion's compute, so it must be priced at the real size, not assumed at 14B; and (2) a 1–2B JEPA may itself be **SRAM-resident and compute-bound**, so the two families share *structure* (iterated transformer inference) but not *operating regime* — the union then over-provisions HBM bandwidth (idle in JEPA mode) and compute (idle in DreamZero mode) more asymmetrically than a naive "few watts of leakage" implies. **The simulator must sweep JEPA predictor size and price the leakage at the real operating point; do not hardcode JEPA at 14B.** ([V-JEPA 2 = 1.2B](https://ai.meta.com/blog/v-jepa-2-world-model-benchmarks/); [DINO-WM](https://arxiv.org/abs/2411.04983))

**Net recommendation:** build both simulators (B as deltas on A), then let the measured DreamZero-workload perf/watt gap between A's specialized point and B's union point decide. The prior above says that gap is single-digit percent as long as the 14B working set exceeds head-power SRAM — which it does by ~3–5×. If the simulator confirms it, ship the general architecture: it costs a few percent and a few watts of leakage on the workload you care about today, and it removes the industry-pivot risk entirely.

---

## Build order

1. Implement A's Tier-1 core; calibrate against your B200 fork runs and DreamZero anchors; produce the DreamZero feasibility region and the Thor comparison. *(Proves the concept.)*
2. Add B's JEPA generator + reuse-axis abstraction; find the union provisioning point; measure the A-vs-B gap on DreamZero. *(Prices the hedge.)*
3. Promote only the surviving design point(s) to Tier 2 (energy) and Tier 3 (scheduling), then Tier 4 for tapeout.
