# PROGRAM.md — the research program, one project per ladder rung

**Written 2026-08-17.** Every architecture idea in this repo, divided into projects:
each ladder level lists its multiplier, its honest range, and the work that unlocks it.
Projects are separate simulator branches evaluated by one ledger; combined
architectures are recomputed, never multiplied.

| Level | Predicted | Likely range (90%) | What unlocks it |
|---|---|---|---|
| **First silicon** | 2.9× | 2.7–6.7× | the etch: zero-instruction static schedule; FP4 systolic + FP8 attention datapath; weight-stream conveyor with CFG-pair sharing; fused attention; v1 compiler |
| **Mature compiler** | 4.2× | 3.9–9.7× | same silicon; compiler extraction 0.55 → 0.80 |
| **Optimized** | ~8× [T] | 6.0–9.7× [T] | memory rebuilt around the model, plus the compute substrate that converts it into speed |
| **Codesign** | ~12× [T] | 7–19× [T] | the model designed together with the silicon |
| **Ceiling** | — | ~35–47× | physics only: every joule in FP4 arithmetic at its floor — the absolute bound at matched precision; beyond it, gains must come from the model |

Likely = the central 90% of the identity sampled over the stated input intervals at
each compiler stage [S]. Outer bounds (every input at its corner): 9.1× first silicon;
15.7×, 22× gated, mature — the top of the mature bound is the north star; ≤ 20–44×
optimized (the mature corner × the 1.3–2× locality band, × gated circuits at the top).
The ceiling row is not a level: no work unlocks it — it is the FP4 arithmetic wall. Optimized-level
numbers are mechanistic-study outputs, gated on the phase-0 macro measurements.
Codesign = optimized × the co-design residual (1.2–2×, the efficiency a model shaped to
this silicon holds that a GPU cannot copy) [T]; ~45× is the FP4 physics wall — beyond
it a ratio is a model-capability claim, measured on robots.

## Technical Roadmap

### First silicon (2.9×; likely 2.7–6.7×)

- Instrument the ledger with per-tensor lifetimes, bytes×distance, and an energy Sankey.
- Bench a real Thor at 40 W on the frozen workloads, predictions registered first.
- Synthesize the FP4 tile, a CIM macro, and a ROM weight-bank macro on one node; extract
  post-layout energy.
- Characterize the critical blocks against the PDK.
- Run a scaled RPU on FPGA; validate predicted vs real activity counts.
- Schedule the full transformer block as one streaming computation, intermediates freed
  at their consumer.
- Bank SRAM by tensor class with producer→consumer placement (including
  transpose-capable buffers); compare interconnect topologies by bit-mm.
- Compare weight-stationary vs streamed vs broadcast dataflows on the exact shapes
  (MACs per fetched weight byte).
- Capture FP8/FP4 anchors on the local RTX proxy to collapse the precision-scaling prior.
- Derive the datapath fraction from the itemized post-PDK ledger.
- Ingest a memory-bound B200/WAN profiling anchor; identify realized bandwidth
  utilization, re-locate the compute/bandwidth crossover, and set the MACs-vs-channels
  provisioning ratio.
- Stand up the tiered simulation harness (SCALE-Sim-class array sim + Accelergy-class
  energy + Ramulator-class DRAM) that every later gate uses.
- Score every candidate across model families (world-action, VLA, JEPA-class) through
  identical accounting — generality is tested, never assumed.

### Mature compiler (4.2×; likely 3.9–9.7×)

- Profile partner workloads on the FPGA; close predicted-vs-realized schedule gaps.
- Fuse the operator tail (norms, RoPE, activations, residuals).
- Deepen DMA overlap toward full hiding.
- Gate idle clocks in schedule bubbles.
- Fabricate the sub-V_min test-structure tile; measure error rates and recovered energy
  (arms the gated ×1.4).

### Optimized (~8× [T]; likely 6.0–9.7×)

- Widen the interface to 512-bit class; implement lossless weight-stream compression
  with one-weight-per-clock decode; evaluate processing-in-memory for the KV window.
- Desk-study 3D thermals (refresh vs temperature, fanless head) and the custom-DRAM
  supply chain.
- Hybrid-bond stacked DRAM with per-bank compute clusters (bank → local SRAM → cluster).
- Pipeline operators vertically across stacked tiers, register to register.
- Design the QK→softmax→PV engine: writable-CIM and spatial-fabric candidates, scored
  on the same block ledger.
- Measure complete-linear-layer energy of the CIM and ROM/shared-product macros against
  the best systolic implementation.
- Define the programmable adapter region (W = W_fixed + AB) and the mask-respin update
  path for hardened weights.
- Recombine the winning substrates into one dual-mode tile; rerun the full-system ledger.

### Codesign (~12× [T]; likely 7–19×)

- Certify quality floors for cross-chunk reuse, sliding-tile attention, token merging,
  and step distillation on robot evaluations.
- Co-train model variants shaped to the memory hierarchy; measure quality on robots,
  never proxies.

### Deadline guarantee (miss-rate < 10⁻⁴)

- Implement CFG pair-sharing and the rolling-KV shift-register window in hardware.
- Close deterministic timing end-to-end; certify the miss rate with cycle-approximate
  + DRAM simulation.
- Co-design the thermals; ship a reference thermal design with the part.
- Implement the microcode mode sequencer and the flow-ODE/CEM update engine.

## Status and gates, per work item

- **Ledger extension** — extend `rpu/ledger.py` with per-tensor lifetimes, bit-mm, Sankey (ledger exists; NoC distance is the gap).
- **Measurement campaign** — Thor bench @40 W; three-macro synthesis (FP4 tile, CIM macro, ROM/product-bank macro); PDK; scaled FPGA. **This is phase 0**; it prices every [T] below.
- **Compiler program** — extraction 0.55 → 0.80; the largest committed multiplier; gated by FPGA + partner-workload profiling.
- **Streaming block schedule** — whole-block schedule, intermediates die at their consumer (fusion result 56.7× exists; explicit schedule doesn't).
- **SRAM banking + interconnect** — tensor-aware banking, placement, bit-mm metric; = Phase 4.5, the model's stated blind spot; could be negative.
- **Weight-dataflow comparison** — stationary vs streamed vs broadcast on exact shapes (= CHIP_ROADMAP gate 1); sets the bar the static-substrate candidates must beat.
- **Sub-threshold-voltage tile** — sub-V_min domains, droop scheduling; measured adverse on stock silicon; unlocked only by the test tile; never counted in bars.
- **Memory widening + compression** — 512-bit-class interface, weight-stream compression 62–83%, LPDDR6, PIM-for-KV (~1.1–1.4×).
- **3D integration** — hybrid-bonded stacked DRAM (8–16 GB over 100–200 MB SRAM; ledger-priced ×1.16 today; bank-local 1.3–2× [T]) AND vertical register-to-register operator pipelining across stacked compute tiers (3D-Flow-class, ~1.5× [X*, 7g]); thermal + supply kill questions open, shared by both halves.
- **Static-substrate decision (CIM vs hardening)** — weight-resident CIM vs FixedWeight hardening, rivals for one slot; screened 1.19× / 1.28× over B1; ≥2× on the complete linear layer or the slot stays digital.
- **Dynamic-attention engine** — substrate-agnostic g_A, the load-bearing term in every study; screened 1.20× (CIM variant); success implies the memory program (every pivot-grade corner is memory-bound).
- **Hybrid transformer tile** — recombination of the static-substrate and attention-engine winners; screened 1.48× central, Gen-3 band 6.0–9.7×; reopens on the macro measurements.
- **Workload levers** — Ledger B (certified reuse floors, tile attention, token merging, distillation); fenced: robot-measured quality only.
- **Deterministic schedule & safety** — the guarantee project (= Phase 3): CFG hardware sharing, rolling-KV window, deterministic timing, miss-rate certification (Tier-3 + DRAM sim), thermal co-design, the flow-ODE/CEM update engine. Unlocks deployability, not a multiplier — which is why a rung-only map missed it (union check, 2026-08-17).

## Binding couplings (the branches are a partial order, not a menu)

1. **Attention engine ⇒ memory program**: any pivot-grade compute gain goes memory-bound at the contract
   interface (~1.95× conversion cap, CIM study ideal row) — an attention breakthrough
   automatically promotes the memory program.
2. **CIM vs hardening**: rivals for one slot; the three-macro synthesis run prices both at once.
3. **Dataflow winner sets the substrate bar**: the dataflow winner is the bar the substrate branches must clear —
   CIM/hardening beat the *best* conventional implementation or nothing.
4. **Streaming schedule ↔ SRAM banking**: the fused schedule determines the traffic pattern banking must serve —
   separately attributable via the ledger, not physically independent.
5. **3D content shifts under hardening**: hardening removes the weight half of 3D's absolute
   saving while the relative increment survives on the leaner total (tested,
   `tests/test_radical.py`).
6. **Workload levers are fenced**: quality-equivalence across model changes is UNSUPPORTED by the
   instrument; nothing from the workload levers enters a hardware ratio.

## What "done" looks like

Each project ends by moving its rung's number from [T] toward [P]/[M] grade — or by a
recorded kill. The ladder (WHITEPAPER table / simulation page) is the scoreboard; this
file is the map from ideas to rungs; the studies under `docs/generated/` are the
screens; `docs/review-audit.md` is the trail.
