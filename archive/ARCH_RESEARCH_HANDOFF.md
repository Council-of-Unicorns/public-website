# Research handoff — chip-architecture multipliers for batch-1 edge transformer inference

**Written 2026-08-06.** Self-contained brief for an AI agent (or human) deep-diving
**chip-architecture-only** improvements to our energy multiplier. Everything relevant that
we have already established, evaluated, or killed is here, so you do not re-tread it.
Companion to `HANDOFF.md` (project-wide onboarding); this file is the research-specific one.

**Evidence tags used throughout:** [M] measured by us · [S] our calibrated simulator ·
[X] literature, primary opened by us · [X*] literature, relayed by a research agent,
primary not opened · [T] estimate/target.

---

## 1. The mission, precisely

Find **additional multiplicative energy-efficiency gains from chip architecture alone** —
no model changes (no sparsity, quantization, distillation, MoE), no circuit/device tricks
(a separate completed stream covered those), for **batch-1 transformer inference at
40 W** — beyond a design that already includes: weight-stationary systolic arrays with
8-wide adder trees, fully static compile-time scheduling, FlashAttention-style fusion
(scores never materialized), double-buffered weight streaming, and per-bank DRAM refresh
scheduled into known idle windows.

The score is **η = energy multiplier vs NVIDIA Jetson Thor at equal 40 W head power**.
Current estimate: **2.0× at first silicon, 2.9× mature** (compiler extraction 0.55 vs
0.80 on the same silicon), ceiling 6.7×, defensible downside 1.6×. Success bars:
2.05 / 2.15 / 3.0. Your job: find what raises these **without touching the model**.

## 2. The workload and regime (fixed — treat as physics)

- One forward pass: 14B-parameter diffusion transformer (DiT), d=5120, 40 layers,
  40 heads (head_dim 128), FFN 13824. **3120 new tokens attending 18,720 context
  tokens** — a compute-dense GEMM regime (arithmetic intensity ~15,500 FLOP/byte), NOT
  skinny decode GEMV. 3 diffusion steps per 200 ms control chunk, CFG pair (weights/KV
  shared across the pair).
- Per step: 2.37e14 FLOP, **7.0 GB weights + 7.8 GB KV streamed from LPDDR**, ~1.5 GB
  activations (SRAM-resident). Chunk: 7.1e14 FLOP, 45.9 GB DRAM traffic.
- Precision: FP4 (E2M1) weights, FP8 activations. Thor has native FP4 — **precision is
  baseline parity, not an edge.**
- Budget: 40 W fanless (neck-path thermal ceiling ~92 W is not binding; watts are).
  8 J per chunk at 5 Hz. At 40 W both chips are ENERGY-bound (chunk takes ~1-2 s;
  bandwidth is not binding in the head-to-head; it binds only for the absolute 5 Hz goal).
- Deadline miss is a safety event: target miss-RATE < 1e-4, never a mean. Anything
  introducing variable latency (replay, speculation, handshakes) is disqualified.

## 3. The accounting framework (how a lever must be priced)

η = Thor's achieved pJ/FLOP ÷ (our arithmetic pJ/FLOP ÷ f_ours ÷ compiler-extraction).
Nothing else. To claim a gain, state **which term** it moves and by how much:

| Term | Current value | Provenance |
|---|---|---|
| FP4 arithmetic (E2M1 mult + 8-wide tree accumulate) | 0.0038-0.0057 pJ/FLOP | [T], Horowitz-derived; the old 0.0125-0.0178 was a double count — do not use |
| f_ours (fraction of chip energy reaching multipliers) | 15-25% assumed | [T]. Published silicon: Eyeriss 3-9% [X], Simba ~11% [X*], Hameed ceiling 35% [X] |
| Thor achieved efficiency | 4.8-11.5 TFLOP/W assumed | [T]; spec peak 15.9 [X]. UNMEASURED — the program's biggest open number |
| Compiler extraction | 0.55 launch / 0.80 mature | [T] |
| Chunk energy shares | arithmetic 32-48%, **DRAM 18-37%** (at 32-64 pJ/B = 4-8 pJ/bit), SRAM/clock/control the remainder | [T]/[X]. The DRAM share was briefly published as 3-6% via a pJ/bit-as-pJ/byte error — beware that landmine (§7) |
| Clock + registers in fabricated accelerators | 33-45% of chip power (Eyeriss); scratchpads 33-42% | [X, verified quotes] |
| Array geometry | 81.7% utilization @ 64×64 vs 44.4% @ 256×256 (fill/drain: S+rows+cols−2) | [S] |

## 4. Hard constraints (violating any of these voids a finding)

1. **No model assumptions.** No sparsity (transformers have ~no exact zeros), no
   quantization beyond the existing FP4/FP8 spec, no token pruning, no approximation.
   The control policy must stay bit-exact. The chip must serve both DreamZero-style DiT
   and JEPA-style planning (generality is a product requirement).
2. **Weights never fit on-die.** 7 GB vs ~90 MB SRAM. Any architecture premised on
   weight residency (NorthPole-style) is structurally excluded. Streaming energy has no
   dataflow-level cure (Cerebras's only documented trick is prefetch overlap, which we
   already do) — only interface-level ones.
3. **Deterministic latency.** Static schedule; no reactive hardware needed at runtime.
4. **One utilization model for us and Thor alike** — a lever credited to us must be
   priced as unavailable to Thor only if that is demonstrably true (e.g. Thor's memory
   subsystem is fixed; its schedule is dynamic).
5. **No HBM** (cost), no cryo, no wafer scale. Node: 4-5 nm class. 40 W total.
6. Peak TOPS is meaningless here; only pJ/FLOP-at-sustained matters (energy-bound).

## 5. Already evaluated — do NOT re-tread (verdicts with reasons)

**Dataflow architectures** (stream completed 2026-08-06, sources in §8):
- Groq TSP determinism → **already ours** (static schedule); its silicon validates the
  bet (no caches/arbiters, ~1 TOPS/mm², batch-1 near-peak) but its SRAM-residency pillar
  is excluded. [X*]
- Cerebras weight streaming → prefetch overlap only; **already ours**. [X*]
- SambaNova CGRA / reconfigurable → fabric tax measured (~1.1 TFLOPS/W peak at 5 nm);
  reconfigurability buys nothing at fixed shapes. [X*]
- Tenstorrent grid-of-cores → measured ~2-2.5 FP8 TOPS/W; distributed reactive control
  costs exactly what our f_ours bet avoids. **Counter-evidence in our favor.** [X*]
- TTA / exposed datapath → order of magnitude behind; attacks register files a MAC array
  does not have. [X*]
- Dataflow religion (WS vs OS vs RS) → second-order once blocking is right (Interstellar,
  ASPLOS 2020); adder tree already = spatial psum reduction. [X*]
- MAERI/SIGMA flexible reduction → upside only under irregularity/sparsity we exclude. [X*]
- FLAT attention fusion → **verified already implemented** in our schedule ([X] verified
  verbatim; our sim defaults fused_attention=True).

**Attention & memory hierarchy** (stream completed 2026-08-06):
- Dedicated softmax hardware → 1-3% of power, already budgeted; published "45×" wins are
  vs inflated baselines. [X*]
- KV-PIM (LPDDR-PIM, AttAcc, NeuPIMs) → advantage assumes decode-style KV reuse=1; our
  KV reuse is 3120, already amortized. Simulated only, parts not commodity. [X*]
- Spatial layer fusion beyond attention → our activations already SRAM-resident; the
  published 37.6% win is vs DRAM-spilling baselines. ~1.05-1.15× at most. [X*]
- Operand forwarding networks (Eyeriss v2 HM-NoC, Simba multicast) → within the
  Interstellar convergence band; nothing beats systolic forwarding measurably. [X*]

**Prior completed streams (circuits, numerics — different domain, listed so you skip):**
resonant/low-swing/mesh clocking, wave pipelining, adiabatic, async/QDI, Razor-class
timing speculation, voltage stacking, IVRs, FD-SOI, zero-gating, LNS/posit/L-Mul number
systems — all REJECTED with primary-source reasons recorded in the project's
PERF_LEVERS Ledgers D4-D6. Sub-Vmin wide-slow operation: ~1.2× system, gated, not counted.

**The silicon-survey calibration you must respect** [X*]: no measured chip sustains
anything near 30-50 TFLOP/W on a transformer. Best fully-measured memory-included result:
IBM NorthPole ≈0.25 effective TFLOP/W (total SRAM residency — excluded for us). All
weight-streaming parts measure 0.01-0.05 effective TFLOP/W on decode. High academic
TOPS/W numbers are 28 nm mW-scale chips with DRAM excluded. Claims beyond ~3× over Thor
have no silicon precedent; treat that as a prior, not a prohibition.

## 6. The surviving levers (rank-ordered) and the open questions to deep-dive

1. **DRAM interface architecture — the primary target.** Sequential streams (compiler
   owns layout) + many slow channels + minimal-reach on-package PHY. Reference physics:
   GDDR5 14 pJ/bit vs HBM2 3.97 (MICRO 2017); WideIO 3D 0.9 pJ/bit measured (VLSI 2013);
   LPDDR5X system ~4-8 pJ/bit. At our 18-37% DRAM share → plausible 1.1-1.4× system.
   **Open:** channel-count/width/clock optimum at 40 W; package options (on-package
   LPDDR? LPDDR6 timing); controller/PHY energy split; what Thor's fixed memory subsystem
   pays that ours need not. Spec is currently silent past "256-bit LPDDR5X, 307 GB/s".
2. **SRAM organization for 90 MB.** sqrt-capacity energy curve spans 64× (CACTI/
   Horowitz); streaming wants wide single-port banks, reuse wants small near banks.
   T-REX's transpose-capable buffer: measured 12-20% utilization gain, portable. **Open:**
   the actual bank geometry, and whether our ~35% non-arithmetic-non-DRAM energy share
   drops materially with a specified banking plan.
3. **Multi-array fleet interconnect — our own model's known blind spot.** The geometry
   result (81.7% @ 64×64) assumes linear fleet scaling with NO NoC/imbalance cost; 465
   arrays at 64×64 vs 29 at 256×256. The real optimum is interior and unmodeled (our
   roadmap calls this Phase 4.5). **Open:** published NoC energy/area for accelerator
   fleets at this scale; hierarchical vs flat reduction across arrays; whether 128×128
   with better SRAM wins over 64×64 with NoC tax.
4. **DCIM tiles (1R1W write-while-MAC)** — measured macro 254 TOPS/W @ 4b (TSMC 5 nm,
   ISSCC 2022) [X*]; duplicates weight-stationary reuse, residual win 1.05-1.2× system.
   **Caution:** hardens 4-bit into silicon; our policy path must keep an FP8 escape
   hatch. Rank last; evaluate only if 1-3 disappoint.

## 6b. The 3D direction — added 2026-08-06 after a peer agent's deep-dive (verified)

A second agent's research identified what our three streams missed by scoping to 2D: the
next large jump likely requires changing the **physical organization** of compute and
memory. Its central observation is correct and elegant: **a hybrid-bonded 3D architecture
collapses surviving levers 1-3 (DRAM interface, SRAM organization, fleet NoC) into one
decision**, and it is the first proposal in the program that architecturally attacks the
dominant clock/register/scratchpad bucket (33-45% of measured accelerator power) rather
than nibbling at DRAM or arithmetic.

**Verified anchors** (primary sources opened by us):
- **d-Matrix Pavehawk** [X]: real 3D-DRAM test silicon, **0.4 pJ/bit measured worst-case
  across voltage/temperature** vs 3-4 pJ/bit HBM4 — vendor silicon, not simulation.
  Commercializing as "Raptor" (~2027) via a custom-DRAM partnership.
- **3D-Flow** (arXiv 2602.11016, ICT/CAS) [X]: hybrid-bonded tiers with register-to-
  register vertical pipelining of QK -> softmax -> PV; claims **>60% of post-FlashAttention
  energy is SRAM access** in long-context workloads, 46-93% energy reduction vs its 2D/3D
  baselines. Simulation; mechanism relevant, numbers not transferable to our breakdown.
- Supporting, NOT independently verified [X*]: Intel 18A synthesizable digital CIM
  (ISSCC 2026, 147 TOPS/W INT8 macro at 400 mV); ATLAS silicon-validated 3D-DRAM
  simulator (<=8.57% error); 0.66 pJ/bit near-DRAM Cu-Cu academic result.

**Why it passes the constraint filter:** fully digital and bit-exact; deterministic (a
vertical tier pipeline is MORE static, not less); model-family-agnostic with DCIM-class
coupling only (a QK/softmax/PV tier stack hardens the transformer op chain into the die).
Genuinely asymmetric vs Thor: a shipped product cannot re-stack itself.

**The two kill questions — research these FIRST, both are desk work:**
1. **Thermal.** The proposal stacks DRAM on compute in a FANLESS head. DRAM refresh
   roughly doubles per ~10 C; our junction sits in the hot regime where our own leakage
   analysis already flips sign. Every cited silicon datapoint is actively-cooled
   datacenter hardware. Required: refresh-power-vs-temperature curves for hybrid-bonded
   DRAM at 90-105 C, and the added compute-to-lid thermal resistance of the stack.
2. **Capacity and supply chain.** We need 7 GB. Multi-GB hybrid-bonded stacks are
   2027-class custom-DRAM roadmap items behind vendor partnerships; commodity LPDDR is a
   quiet strength of the current design that this bet spends.
3. **Reliability under robot conditions.** Hybrid bonds under thermal cycling and
   vibration in a moving head; automotive-grade qualification for hybrid bonding is
   nascent. Desk-researchable (JEDEC/automotive qual literature).

**Lock-in analysis (asked and answered 2026-08-06):** the near-term levers are
transformer-general with no new model coupling. DCIM hardens 4-bit (ranked last for it).
The 3D tier stack hardens the attention op-chain: all standard transformer variants (MHA/
GQA/MQA/cross-attn/DiT/JEPA) share QK->softmax->PV and run on it; a post-transformer
shift (SSMs, softmax-free linear attention) would idle the softmax tier and forfeit part
of the vertical win, where a 2D array loses nothing. 3D DEEPENS the transformer-family
bet; it does not create a single-model bet.

**Research-target ladder** (NOT in any headline; gated exactly like sub-Vmin):
interface-only, thermal-permitting ~1.25x (mature 2.9 -> ~3.6x); with vertical-pipeline
SRAM/NoC wins surviving our breakdown, ~1.5x (-> ~4.4x); the aggressive 2x case is not
obviously impossible — the one lever family that attacks DRAM + SRAM + NoC + registers
together — but currently rests on one simulation paper and unbuilt DRAM.

**Evaluation vehicle:** Phase 4.5's fleet-interconnect model prices a vertical tier
pipeline as naturally as a 2D NoC; ATLAS is the external cross-check.

**Adjacent, classified:** analog gain-cell attention (Nature Comp. Sci. 2025) — enormous
claimed upside, violates bit-exactness, targets decode-reuse regime; monitor only.
Photonics — sub-4-bit effective precision, conversion overheads; below 3D electronic
integration for a first RPU. Weight-resident NVM/ROM — structurally mismatched to 7 GB.

**Model-coupling status of all four: none add model assumptions** (the kill-filter above
removed every lever that did). 1-2 need chip-spec work that does not exist yet; 4 narrows
precision flexibility — the one genuine coupling risk.

## 7. Traps that have burned this project (check yourself against each)

- **pJ/bit vs pJ/byte (8×).** We stepped on it ourselves this week ("5 pJ/B" that was a
  pJ/bit-class figure; DRAM share mispublished as 3-6% instead of 18-37%). Always state
  units; any DRAM figure below ~1 pJ/bit is implausible (nothing measured beats WideIO 0.9).
- **Ungated/inflated baselines.** Eyeriss's famous 45% zero-gating was vs an UNGATED
  baseline on 77% zeros; softmax "45×" was vs a 256-core RISC-V. Ask what the baseline is.
- **Decode vs prefill regime.** Most LLM-accelerator literature is decode (GEMV,
  reuse=1). Our regime is 3120-token compute-dense prefill. Wins premised on reuse=1
  (PIM, KV engines) evaporate; check the regime before transferring any number.
- **Peak vs sustained; DRAM-excluded academic chips.** 88 TOPS/W-class figures are 28 nm
  mW parts with EMA excluded. Effective sustained on real parts is 100× lower.
- **A double count hides in relabeled subtotals.** Our own "FP4 multiply" was a scaled
  MAC (accumulate included) plus an accumulator again. Trace every constant to its
  boundary definition.
- **One-directional checks.** For every bound, state what would catch an error in the
  OTHER direction before publishing (our L12).
- **Agent-relayed numbers are [X*] until you open the primary.** This project has a
  recorded fabrication incident. Named source (title/venue/year) for every number;
  NOT FOUND is a valid, useful answer.

## 8. Key sources already in hand (verify against, don't re-find)

Groq TSP ISCA 2020/2022 · Cerebras weight-streaming whitepaper · SambaNova SN40L
(arXiv 2405.07518, ISSCC 2025) · Tenstorrent Hot Chips 2024 · Interstellar (ASPLOS 2020,
arXiv 1809.04070) · FLAT (ASPLOS 2023) · FuseMax (MICRO 2024) · SIGMA (HPCA 2020) ·
Eyeriss JSSC 2017 + v2 JETCAS 2019 · Simba (MICRO 2019) · SpAtten (HPCA 2021) · ITA
(ISLPED 2023) · T-REX (ISSCC 2025, arXiv 2503.00322) · Fine-Grained DRAM (MICRO 2017) ·
WideIO (VLSI 2013) · TSMC 5nm DCIM (ISSCC 2022) · NorthPole (Science 2023; HPEC 2024
LLM) · Hailo-10H independent measurement (arXiv 2603.23640) · Hameed ISCA 2010 ·
Horowitz ISSCC 2014.

## 9. What a good deliverable looks like

A ranked list where each entry states: (a) the mechanism, (b) which §3 term it moves and
by what factor **on that term**, (c) the system-level multiplier after the term's share,
(d) evidence class (measured silicon / simulated / vendor), (e) model-coupling: none /
soft / hard, (f) spec cost (what must be designed that currently is not), (g) what Thor
already has — a lever Thor also enjoys nets zero. End with the single measurement or
spec decision that would most change the ranking. Negative results (X adds nothing
because Y) are first-class findings; several of our best conclusions this week were
negatives.
