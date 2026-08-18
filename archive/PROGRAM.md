# PROGRAM.md — the research program, one project per ladder rung

**Written 2026-08-17.** The division of every architecture idea in this repo into
separately attributable projects. Organizing principle: **each project is the unlock of
exactly one ladder rung, and its success criterion is that rung's multiplier** — so
attribution is automatic (the ledger separates the rungs), gates are inherited rather
than invented, and completeness is checkable: a project with no rung, or a rung with no
project, is visible instantly. One structural exception found and fixed on the union
check: the deadline-miss-rate GUARANTEE is the success metric's other half and unlocks
no multiplier — it carries its own row and project (deterministic schedule & safety). Checked complete against the
union of WHITEPAPER,
ETA_REPORT 7g/7g-bis, PERF_LEVERS, CHIP_ROADMAP, and the three studies (CIM, radical,
fixed-weight) on 2026-08-17.

Rule inherited from the studies: projects are **separate simulator branches evaluated
by one ledger** — never one architecture that accumulates every idea, and never
multiplied multipliers. Combined architectures are recomputed (S15/§22 discipline).

| Level | Multiplier vs Thor | What unlocks it | The work required |
|---|---|---|---|
| **First silicon** | 2.9× | the etch: zero-instruction static schedule; FP4 systolic + FP8 attention datapath; weight-stream conveyor with CFG-pair sharing; fused attention; v1 compiler | extend the energy ledger with per-tensor tracking (lifetimes, bit-mm, Sankey) · run the phase-0 measurement campaign (Thor bench at 40 W, the synthesized macro trio, PDK characterization, scaled FPGA) · implement the whole-block streaming schedule · design tensor-aware SRAM banking and the interconnect (Phase 4.5) · settle the weight-dataflow comparison on the exact shapes |
| **Mature compiler** | 4.2× | same silicon; compiler extraction 0.55 → 0.80 | the compiler program: scheduling, operator-tail fusion, deeper DMA overlap, idle clock-gating — matured by profiling against the FPGA and partner workloads |
| **North star** | 15.7× / 22× gated | every uncertain input resolving favorably; the 22× adds sub-V_min operation | the measurement campaign narrowing the four uncertain inputs from estimates to measurements · the sub-threshold-voltage test-structure tile that arms (or kills) the ×1.4 |
| **Frontier** | ≤ 20–44× | memory rebuilt around the model, plus the compute substrate that converts it into speed | widen the memory interface and compress the weight stream (512-bit-class, 62–83% lossless, LPDDR6, PIM-for-KV) · build hybrid-bonded 3D stacked memory with bank-local compute and vertical operator pipelining (thermal + supply questions first) · design the dynamic-attention engine — the load-bearing term · decide the static substrate: weight-resident CIM vs ROM-hardened weights (rivals, one slot, priced by the same macros) · recombine the winners into the hybrid transformer tile |
| **Horizon** | undefined | the model designed together with the silicon | the workload-lever program under certified quality floors (cross-chunk reuse, tile attention, token merging, distillation) · full model–silicon co-design once the architecture converges — measured on robots, never simulator-only |

The ladder is the multiplier half of the success metric. The other half is a
guarantee, not a multiplier, and gets its own row:

| Deliverable | Target | What unlocks it | The work required |
|---|---|---|---|
| **Deadline guarantee** | miss-rate < 10⁻⁴ | the schedule etch | CFG pair-sharing in hardware · rolling-KV shift-register window · deterministic end-to-end timing · microcode mode sequencer and the programmable update engine · miss-rate certification (cycle-approximate + DRAM simulation) · thermal co-design with a shipped reference design |

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
