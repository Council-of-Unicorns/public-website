# The FM-RPU Whitepaper: A Measured Case for Etching World-Model Inference into a Robot's Head

*Working paper, July 2026. Consolidates the calibrated-simulator results, the chip program
(spec, layout, roadmap), the memory-wall analysis, and the strategy documents into one
argument. Every number carries a provenance tag: **[M]** measured on hardware we ran,
**[S]** computed by our calibrated instrument, **[F]** founder-measured in production,
**[X]** external literature, **[T]** target or estimate.*

*Audience: engineers deciding whether to build this with us. The document states what we
know, how we know it, what we got wrong, and which problems are open.*

---

## Abstract

World Action Models place a 14 B-parameter diffusion transformer inside a humanoid's
200 ms balance loop. That model runs today on a kilowatt datacenter GPU or across a radio,
and both options put facility power or Wi-Fi jitter inside a stability-critical control
path [F]. We characterized the workload at operator granularity, calibrated an analytical
performance model to measured Blackwell silicon within 0.7–4.6 % on latency and energy [M],
and derived the design target for a head-resident accelerator. At head power the binding
constraint is energy rate: chunk time equals chunk joules divided by watts, and peak FLOPS
cancels out of the comparison [S]. Scored at power parity — both
chips at the 40 W head ceiling — the speedup IS the efficiency advantage: S = η. Beating
Thor 2× in the flagship Quality mode needs η ≈ 2.05; beating it SOLIDLY (5th-percentile
S ≥ 2 in every mode, with a 25 % thermal margin granted to Thor) needs η ≈ 2.2–2.8,
inside the published 1.6–3.2× TPUv4-versus-A100 band; the design target is η = 3 [X, S]. Attention consumes ~62 % of dynamic energy, so matrix-multiply
specialization alone caps the speedup at 1.17× and any credible datapath must improve the
attention path [S]. We present the FM-RPU design point (4 PF dense FP4, LPDDR5X conveyor,
40 W), the workload co-design levers that attack the absolute 5 Hz goal, and a roadmap in
which a kill test gates every funding tier.

## 1. Robot control converged on a workload that has no chip

The leading humanoid programs now drive motion from latent world models: a video-action
diffusion transformer imagines the next two seconds and emits an action chunk, re-planned
five times per second [X: DreamZero, 1X]. A missed 200 ms deadline is a stability event.
The robot is mid-step when the answer arrives late.

The founder built both current alternatives and measured their failure [F]. Distilling the
diffusion schedule from 16 steps to 3 reached control rate on two B200-class GPUs per
robot, a kilowatt of datacenter silicon each. A production remote-inference stack (custom
media-over-QUIC transport, CFG parallelism across GPUs, velocity caching, PyTorch graph
capture, train-time chunking) then moved that compute off-robot. Iso-compute simulation
puts the on-head deadline miss rate near zero and the busy-Wi-Fi miss rate at 7.8 %,
against a 10⁻⁴ stability target [S]. Remote inference fails on certification under jitter.
The inference must live in the head, and the only deployable head silicon, a
general-purpose SoC, runs this workload roughly 20× too slow at head power [S].

## 2. The workload is one shape-stable transformer loop

Defaults follow Wan2.1-I2V-14B / DreamZero geometry: 14 B parameters, d = 5120, 40 layers,
FFN 13 824, 40 heads, 1 560 tokens per latent frame, a 2 s rolling window of
N_ctx ≈ 18 720 tokens, 1 560–3 120 new tokens per step, 1–3 denoising steps, a classifier-free-guidance (CFG) pair,
200 ms control period. Four-bit weights occupy 7.0 GB; the FP8 KV window occupies a
comparable 7.7 GB. Neither fits head-power SRAM, so both stream from DRAM every step [S].

One denoising step splits as: self-attention 38.7 % of FLOPs, FFN 28.6 %, QKV projection
15.9 %, cross-attention 10.9 %, output projection 5.3 % [S]. With CFG fan-out the step
reads 14.8 GB once and computes both guidance branches; naive double-fetch would double
that. Arithmetic intensity is ≈ 1.7 × 10⁴ FLOP/byte, far above every edge ridge point, so
the loop is compute-bound in the classical roofline sense [S]. Section 9 explains why that
margin still requires engineering.

## 3. At head power, energy rate sets latency

A fanless head rejects ~40 W through the neck [S: thermal model]. That ceiling is a
transport property of the neck path; Section 6.1 treats it as a design surface, and this
section holds it fixed for every contender. Chunk time obeys four bounds, and the fourth
dominates:

t = max( t_compute, t_memory, t_comm, E_chunk / (TDP · (1 − f_static)) ).

At the three-step operating point the energy bound exceeds the roofline bound by an order
of magnitude on Thor and on the FM-RPU alike [S]. Raising peak FLOPS without lowering
joules per FLOP moves nothing. When both devices sit on the energy bound with shared
coefficients, throughput cancels and the speedup reduces to an identity:

S = η · (TDP_dut / TDP_base),

where η is the per-FLOP energy advantage of the design point over the calibrated GPU
datapath [S]. At parity a part with η = 1 exactly ties Thor, and every point of speedup
is a point of efficiency. The entire product question compresses into one number.

## 4. The instrument earned its extrapolation rights on measured silicon

Reproducing built silicon gates every extrapolation to unbuilt silicon. Four authoritative
anchors ran on an RTX PRO 6000 Blackwell workstation: shape-faithful BF16 chunk proxies at
one, two, and three steps, with board energy from mean `nvidia-smi` power times duration
[M]. The fitted model reproduces all four within 0.7–4.6 % latency and 0.2–2.4 % energy;
fitted compute utilization is 0.84 [M]. Placeholder anchors for Thor and B200 fail the
gate at 40–65 % error and carry no authority [S].

Two further measurements killed our own easiest stories [M]:

1. **DVFS is flat.** Energy per FLOP is constant from 1.0 to 3.1 GHz (η_V/f = 1.00, idle
   power subtracted and audited). The wide-and-slow voltage win requires sub-Vmin custom
   design; it is unavailable from operating points on this silicon.
2. **Precision scaling underdelivers.** FP16→FP8 measures 1.77–1.82×, under the nominal
   2× per halving. We hold the FP16→FP4 energy scale as a measured-anchored prior
   s ~ U(2.6, 3.4), which tripled our absolute energy estimates when it replaced the
   assumed s ≈ 10.

We publish adverse results and re-derive every downstream number when one lands. That
discipline is the working method, and Section 12 states it as policy.

## 5. The target: η ≈ 2.2–3 at power parity, and it cannot come from matmul alone

Monte Carlo over token count, step compression, and the precision prior gives
η\* = 2.05 for median S = 2 in the flagship Quality mode against Thor held to the 40 W
neck ceiling; the closed form 2 × 40/40 = 2 checks it [S]. The success criterion is the
SOLID beat: 5th-percentile S ≥ 2 in every mode (η ≥ 2.15), with a design target of η = 3
that holds even if Thor's in-head budget proves 25 % better than our thermal estimate
(50 W → η ≥ 2.80) [S]. The solid bar sits mid-band in the TPUv4 evidence and the target
at its top, so the stacked levers (realized-utilization edge, workload-shaping
realization, sub-Vmin) buy margin on top rather than carrying the claim; Section 9 still
owns them. Against Thor's 130 W module rating the same design point reaches S ≈ 0.66 at
the solid bar and 0.92 at the target; the FM-RPU is a head part, and we say so [S].

The published evidence brackets the target. TPUv4 delivered 1.6–3.2× perf/W over the
same-node A100 on measured power [X: ISCA 2023]. Hameed et al. showed that a
general-purpose baseline spends 5.8 % of energy in functional units (FU), that fused custom
datapaths raise that fraction toward ~35 %, and that custom storage wired to functional
units, and neither instruction removal nor SIMD width, carries the processor-to-ASIC gap
[X: ISCA 2010]. Tensor cores already implement the fused-matmul stage, so our advantage
must come from the fabric around the MAC: pipeline and clocking (22 % of the Hameed
ledger), caches (19 %), register files (10 %), control (10 %).

Attention sharpens the requirement. With the mid prior, dynamic energy splits ~62 %
attention, 36 % matmul and projection, 2 % bytes, because attention runs FP8 against FP4
linears [S]. Zeroing matmul energy while leaving attention unchanged caps the speedup at
1.17×. Reaching S = 2 by matmul specialization is impossible under this split. The
attention energy path (online-softmax streaming, FLASH-D-style division hiding, fused
exponential-multiply operators, and a static per-layer max bound that our fixed geometry
permits) is load-bearing for the thesis [X: arXiv 2505.14201, 2505.14314; S].

## 6. The FM-RPU design point

A head-resident inference engine sized to the shapes above [T unless tagged]:

- ~1.9 M FP4 MACs at ~1.05 GHz (4 PF dense) in 128×128 weight-streaming systolic tiles;
  the widths divide the array exactly (5120 = 8 × 640, 13 824 = 8 × 1728).
- FP8 multiply into FP32 accumulators in dedicated SRAM below the array, TPUv1's
  narrow-multiply wide-accumulate pattern [X].
- A 256-bit LPDDR5X conveyor at 307 GB/s and ≥16 GB. The prefetcher is a counter: the
  chip reads the identical ~44 GB address sequence every chunk. ~90 MB of on-die SRAM
  holds stream buffers and the activation spine, and never a resident weight set.
- A DRAM-resident KV ring that advances by pointer at chunk end. The conveyor fetches
  weights and context KV once per step and fans them out to both CFG branches in silicon.
- **Refresh inside the schedule.** The sequencer issues per-bank refresh in
  statically-known conveyor-idle windows. Hot-head refresh derating otherwise taxes
  14–28 % of effective bandwidth and injects tail latency; scheduled refresh zeroes the
  interference by construction [X: JEDEC timing; S].
- **Zero-OS execution.** The same chunk costs ~1 200 kernel launches on a GPU and zero
  in-band instructions here. Determinism is throughput in this regime: under a 7 ms p99
  bound the TPU held 80 % of peak while the same-node K80 fell to 37 % [X: ISCA 2017].
  Our 200 ms loop is a tighter latency-bound regime than that benchmark.
- A microcoded schedule ROM (1/2/3-step modes) produced by an offline tool,
  `fmrpu-schedule`, that reuses the calibrated simulator as its cost model and emits a
  per-mode worst-case deadline certificate. Weights, scales, token counts, and schedules
  load from an image; tile geometry and datapath formats are mask-fixed.
- A programmable update block (~2 % of datapath) runs flow-ODE or CEM-style planning.
  Supporting a JEPA-family workload costs 1.9 % DreamZero-path perf/W at this design
  point; both families stream 7 GB weights, so no memory tier separates them [S].

Modes at the solid bar η = 2.15 against Thor-in-head [S]: **Quality (3-step CFG), the
flagship: 6.2 s vs 13.0 s, S = 2.10**; Balanced (2-step) 4.1 s vs 8.6 s, S = 2.10;
Deadline (1-step distilled, N = 1560) 0.56 s vs 1.14 s, S = 2.05. Every mode clears 2× at
the solid bar; at the η = 3 target Quality reaches 2.86×. No mode meets an absolute
200 ms; the analytical model puts that at η ≈ 12 (η ≈ 6.4 in Deadline mode), outside
every evidence band. Closing the absolute gap belongs to the workload levers below.

### 6.1 Heat removal carries the same leverage as η

Speed at head power scales one-for-one with rejected watts (Section 3), so the thermal
path is a performance component, and the architecture supplies three thermal properties a
general-purpose module cannot [T]:

1. **A compile-time power trace.** The etched schedule fixes each cycle's power draw, so
   the package guardband shrinks to process variation and the reactive governor
   disappears. A GPU reserves thermal margin for its worst uncharacterized burst and
   throttles under transients, which injects tail latency straight into the deadline
   budget. The zero-interference argument for scheduled refresh extends to thermal
   transients.
2. **Flat, low power density.** The floorplan spreads its 40 W budget over ~450 mm²,
   under 9 W/cm² with uniform systolic activity [T]. Thor concentrates a 130 W-class die behind
   the same ceiling. Low flat density keeps the head fanless and pumpless, and the
   wide-and-slow direction lowers it further, so the thermal argument and the sub-Vmin
   argument point the same way.
3. **Schedule-aware thermal shaping.** The µcode knows future power the way the conveyor
   knows future addresses, so the scheduler interleaves compute-dense and memory-dense
   phases by construction.

Transport upgrades attack the 40 W ceiling itself: sub-3 mm microchannel cold plates are
the mainstream cooling path for high-power humanoid compute today [X], neck heat pipes
move rejection into a torso radiator, and embedded microfluidics extracts 700–1,700 W/cm²
at die level in laboratory demonstrations [X]. Every transported watt buys linear speedup
on the energy bound; a 40→60 W neck path multiplies S by 1.5. Fairness bounds the claim:
transport serves any chip, so it enters the model symmetrically for every hardware row
and never counts toward η [S-policy]. The asymmetries that survive are the guardband, the
density, and shipping the reference thermal design with the chip. Microfluidic co-design
also pairs with the gen-2 3D-DRAM supply step (Section 8), whose weakest point is heat
extraction through the stacked die.

## 7. Workload co-design multiplies what silicon delivers

We scrutinized each candidate lever against its literature and kept survivors with
per-mode multipliers on chunk energy [X/T, task-success gated]:

| Lever | Verdict | Quality mode | Deadline mode |
|---|---|---|---|
| Cross-chunk reuse (receding-horizon overlap) | upgraded: WorldCache reports 2.3× at 99.4 % quality on a video world model; Chorus reports 1.45× on 4-step distilled models | 1.3–2.0 | 1.0–1.45 (certified floor) |
| Sliding-tile sparse attention | survives, trimmed | 1.15–1.45 | 1.15–1.45 |
| Token merging | survives, cautious | 1.1–1.3 | 1.1–1.3 |
| Softmax simplifications | survives, minor | 1.01–1.03 | 1.01–1.03 |
| Per-step feature caching | refuted at 1–3 steps (serving literature: ineffective on 4-step distilled models) | 1.0–1.2 | 1.0 |

Composed with an overlap discount: ≈1.7–3.8× (Quality) and ≈1.4–2.6× (Deadline) [T].
Cross-chunk reuse is the flagship: consecutive chunks re-diffuse overlapping world state,
the mechanism class that survives few-step schedules, and the one no LLM accelerator has
a reason to build. In Deadline mode the schedule reserves the worst-case slot, so dynamic
reuse saves energy while the miss-rate proof stands; a reuse floor counts against the
deadline only when training guarantees it. The founder's train-time chunking is the tool
that can train that floor in [F].

A recorded design constraint bounds this section: the control policy must not depend on
aggressive quantization (INT2 weights, FP4 KV, 2:4 pruning) [F]. Those levers remain
last resorts behind bit-exact and structural options.

## 8. Engineering the memory wall, honestly

WAN-class video models (the Wan2.1 family) measure memory-bandwidth-bound on B200 [F], while our fused model calls
the loop compute-bound. Three findings reconcile the two. First, unfused attention
materializes 2.3 GB of scores per layer, ~25× our entire stream; a GPU's memory-boundedness
is partly manufactured by imperfect fusion, and an etched pipeline makes the fused byte
count a guarantee [S]. Second, batch-1 execution collapses weight reuse on GPUs, moving
the operating point across the roofline crossover our design document predicted. Third,
our instrument holds no memory-bound anchor yet, so its memory-regime numbers are the
least trusted in the model; ingesting the founder's B200/WAN profiling is a gate-1
requirement [F→M].

The candidate config sits 1.5× on the compute side of its ridge, and hot-head refresh
nearly closes the margin [S]. The solution ladder holds bit-exact demand cuts (lossless
entropy coding of the weight stream at ×0.62–0.83, with demonstrated one-weight-per-clock
decoders [X]) and linear-cost supply steps: 512-bit LPDDR5X at 614 GB/s (Apple ships
546 GB/s on-package today), LPDDR6 at ~2.25× per package in 2026, LPDDR6-PIM executing KV
passes in-bank (Samsung and SK hynix are standardizing it), and hybrid-bonded 3D DRAM at
0.66–0.88 pJ/bit for a second generation [X]. A conservative profile with FP8 weights and
no aggressive quantization streams ~15.5 GB per step and fits inside the compute shadow at
512-bit LPDDR5X [S]. MAC area trades ~linearly for PHY channels, so the compute-to-bandwidth
ratio is a gate-1 decision against the ingested anchor, and never an afterthought.

**Verdict: a solution exists at every priced severity; gate 1 selects the rung.** The
worst case forces the 512-bit interface plus entropy coding, both ordinary engineering,
and every rung honors the no-aggressive-quantization constraint [F]. The single open item
is a measurement: ingest the founder's B200 profiling at gate 1 and read off which rung
the real workload needs.

## 9. Open problems: what you would own

Every problem below is open, carries load, and comes with instrumentation that measures progress.

1. **The attention energy path.** Design the streamer that makes 62 % of dynamic energy
   cheap: division-free online softmax, fused exp-multiply, static max bounds, and the
   dataflow split between fabric passes. The thesis fails without it (Section 5).
2. **The dataflow A/B.** Weight-stationary vs output-stationary vs broadcast-tree on our
   exact shapes, per pass, in Timeloop; a stall-free conveyor removes output-stationary's
   usual advantage and nobody has published this comparison for chunk diffusion.
3. **The Tier-2 energy ledger.** Build the Accelergy-class tile model and produce our
   Hameed-Table-3: per-component mJ/chunk. Kill criterion: mapped η < 2.2 or FU fraction
   < 35 % ends the project before tapeout money; the 2.2 line sits just above the 2.15
   success bar, so the kill test and the success test have nearly merged.
4. **The memory-bound anchor.** Ingest real B200/WAN profiling, identify bw_util (the realized
   bandwidth-utilization coefficient), place
   the crossover, and set the MACs-versus-channels ratio.
5. **Sub-Vmin operation.** Etched claims half-voltage math blocks in A0 silicon; the
   near-threshold literature offers split domains, 8T SRAM, and Razor-class margin
   recovery (~47 % measured). Prove it on a test tile or leave it out of η forever.
6. **The certified reuse floor.** Co-design train-time chunking with the scheduler so
   cross-chunk reuse carries a trained, certifiable minimum, converting a heuristic into
   deadline credit.
7. **The robot memory engine.** Persistent latent state, episodic retrieval, fast-weight
   layers, and bounded context in hardware. A write-capable weight path breaks the
   read-only conveyor assumption, so scope it before RTL freezes that assumption.
8. **The compiler.** `fmrpu-schedule` today; a PyTorch→StableHLO→MLIR backend as the
   platform grows. The moat is compiler plus scheduling plus memory hierarchy, and the
   cost model already exists as the calibrated simulator.
9. **Deadline-mode existence.** Distill to 1-step at reduced tokens with task success
   intact. Without it, Deadline mode has silicon and no workload [F-adjacent, model team].
10. **The thermal reference design.** Co-design the package, neck transport, and torso
    rejection around the schedule's power trace; quantify the guardband a compile-time
    trace recovers; and test whether embedded microfluidics makes the gen-2 3D-DRAM
    supply step thermally viable (Section 6.1) [T].
11. **HBM, reconsidered.** The early rejection of HBM rests on power, cost, and the
    conveyor's modest bandwidth need, and it predates the calibrated model [T].
    Single-stack HBM3E stays an explicit fallback in the memory ladder; re-price it
    against the gate-1 anchor alongside the LPDDR rungs so the ruling rests on measured
    numbers.

## 10. Roadmap: a kill test gates every dollar tier

| Gate | Resolves | Cost | Kill condition |
|---|---|---|---|
| 1. Tier-2 tile energy model (Timeloop/Accelergy) + dataflow A/B + memory anchor | first computed η for this datapath | ~$0, weeks | η < 2.2 or FU < 35 % |
| 2. Jetson Thor baseline measurement | the denominator of the success metric | ~$3 k, days | model misses measured Thor badly |
| 3. MAC tile + conveyor RTL on FPGA (AMD Versal class) | measured η for the core datapath, bit-exact vs the golden model | ~$1–2 M, 2–3 quarters | measured η under the Tier-2 claim |
| 4. Test-structure shuttle (includes the sub-Vmin tile) | η on our silicon at our voltage | low $M, ~1 year | silicon under FPGA-projected η |
| 5. Production tapeout, N4-class | the product | $30–50 M | only after gates 1–4 pass |

The funding shape follows the gates: a $3–4 M pre-seed runs gates 1–3 to an FPGA-proven
η and a design-partner LOI; $8–15 M funds the shuttle; $30–60 M funds production [T].
Equipment for the first year: Thor devkits, AMD Versal FPGA boards (VEK280 class), cloud
GPUs, and a power-measurement bench.

## 11. Strategy in one page

The socket is the humanoid head, won per robot generation, and defended by certification:
deterministic timing, once inside a safety case, is a moat measured in years. Competitors
each miss one constraint: Thor stays general because CUDA is the product; datacenter
transformer ASICs sit 20× off in power regime; edge NPUs are ~100× too small for a 14 B
streaming model. The relative bar (2× Thor-in-head) rides on η and clears in every mode;
the absolute 5 Hz loop is a joint model-and-silicon program (Sections 6–7), and we state
that in public documents. Datacenter ASIC marketing numbers answer a different question.

## 12. How we work

1. **Measurement first.** No extrapolation without reproducing built hardware; our measurement-first gate (P6)
   blocked every feasibility claim until real anchors landed, and it still governs.
2. **Adverse results ship.** The DVFS null, the 1.77× precision result, and the corrected
   5 Hz claim are in the record with the same prominence as favorable numbers.
3. **Provenance on every number.** [M]/[S]/[F]/[X]/[T] tags appear in every document,
   including this one; an untagged number is a bug.
4. **Kill tests before dollars.** A gate that cannot fail is theater. Ours name the
   number, the threshold, and what dies when it misses.
5. **One instrument, identical rules.** One utilization model scores every hardware row;
   the design under test never receives a friendlier assumption than the incumbent.

If that method and Section 9's problems read as the job you want, the instrument, the
data, and the open questions are in this repository. The silicon is waiting on you.

## References

1. DreamZero authors, "World Action Models are Zero-shot Policies," arXiv:2602.15922, 2026.
2. Q. Shen et al., "World Action Models: A Survey," arXiv:2606.20781, 2026.
3. N. Jouppi et al., "In-Datacenter Performance Analysis of a Tensor Processing Unit," ISCA 2017.
4. N. Jouppi et al., "TPU v4: An Optically Reconfigurable Supercomputer…," ISCA 2023.
5. R. Hameed et al., "Understanding Sources of Inefficiency in General-Purpose Chips," ISCA 2010.
6. FLASH-D, arXiv:2505.14201; ExpMul, arXiv:2505.14314.
7. WorldCache, arXiv:2603.22286; Chorus (inter-request caching), arXiv:2604.04451; STA, arXiv:2502.04507.
8. R. van Erp et al., "Co-designing electronics with microfluidics for more sustainable
   cooling," Nature 585, 2020; flexible cold plates for humanoid chips, Device,
   10.1016/j.device.2024 (S2666-9986(24)00498-8).
9. Repo companions: `CHIP_SPEC.md`, `CHIP_LAYOUT.md`, `CHIP_ROADMAP.md`, `PERF_LEVERS.md`,
   `MEMORY_BANDWIDTH.md`, `papers/FMRPU-memo-v2.pdf`, calibrated instrument (`fmrpu/`),
   measured data (`fixtures/measured/`, `fixtures/dvfs_sweep.json`).
