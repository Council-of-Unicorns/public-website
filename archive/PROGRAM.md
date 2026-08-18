# PROGRAM.md — the research program, one project per ladder rung

**Written 2026-08-17.** The division of every architecture idea in this repo into
separately attributable projects. Organizing principle: **each project is the unlock of
exactly one ladder rung, and its success criterion is that rung's multiplier** — so
attribution is automatic (the ledger separates the rungs), gates are inherited rather
than invented, and completeness is checkable: a project with no rung, or a rung with no
project, is visible instantly. One structural exception found and fixed on the union
check: the deadline-miss-rate GUARANTEE is the success metric's other half and unlocks
no multiplier — it carries its own row and project (P-D). Checked complete against the
union of WHITEPAPER,
ETA_REPORT 7g/7g-bis, PERF_LEVERS, CHIP_ROADMAP, and the three studies (CIM, radical,
fixed-weight) on 2026-08-17.

Rule inherited from the studies: projects are **separate simulator branches evaluated
by one ledger** — never one architecture that accumulates every idea, and never
multiplied multipliers. Combined architectures are recomputed (S15/§22 discipline).

| Level | Multiplier vs Thor | What unlocks it | Projects necessary |
|---|---|---|---|
| **First silicon** | 2.9× | the etch: zero-instruction static schedule; FP4 systolic + FP8 attention datapath; weight-stream conveyor with CFG-pair sharing; fused attention; v1 compiler | I0 Ledger+ · I1 Measurement campaign · P1 Streaming block · P2 SRAM+NoC (Phase 4.5) · P3 Dataflow A/B |
| **Mature compiler** | 4.2× | same silicon; compiler extraction 0.55 → 0.80 (scheduling, tail fusion, DMA overlap, idle gating) | P-C Compiler |
| **North star** | 15.7× / 22× gated | every uncertain input resolving favorably (FP4 arithmetic at its floor, datapath fraction at the 35% ceiling, near-ideal compiler); the 22× adds sub-V_min operation | I1 (narrows the inputs from [T] to measured) · P-V Low-voltage test tile (arms the ×1.4) |
| **Frontier** | ≤ 20–44× | memory rebuilt around the model — 3D bank-local stacked DRAM (reads ~40 → ~8 pJ/B) and/or widened interface + compression — plus the compute substrate that converts it: attention engine, CIM-vs-hardening winner, hybrid tile | P4-M1 Memory widening + compression · P4-M2 3D bank-local · P6 Attention engine · P5/P5′ CIM vs hardening (rivals) · P7 Hybrid tile |
| **Horizon** | undefined | the model designed together with the silicon: memory shaped to its reuse, operators as pipelines, precision only where needed | P-W Workload levers (Ledger B), quality-gated → co-design at convergence |

The ladder is the multiplier half of the success metric. The other half is a
guarantee, not a multiplier, and gets its own row:

| Deliverable | Target | What unlocks it | Projects necessary |
|---|---|---|---|
| **Deadline guarantee** | miss-rate < 10⁻⁴ | the schedule etch: CFG pair-sharing in hardware, rolling-KV shift-register window, deterministic end-to-end timing, microcode mode sequencer, programmable update engine, thermal co-design with a shipped reference design | P-D Deterministic schedule & safety (= CHIP_ROADMAP Phase 3) |

## Project index (one line each; status points into the studies)

- **I0 Ledger+** — extend `rpu/ledger.py` with per-tensor lifetimes, bit-mm, Sankey (ledger exists; NoC distance is the gap).
- **I1 Measurement campaign** — Thor bench @40 W; three-macro synthesis (FP4 tile, CIM macro, ROM/product-bank macro); PDK; scaled FPGA. **This is phase 0**; it prices every [T] below.
- **P-C Compiler** — extraction 0.55 → 0.80; the largest committed multiplier; gated by FPGA + partner-workload profiling.
- **P1 Streaming block** — whole-block schedule, intermediates die at their consumer (fusion result 56.7× exists; explicit schedule doesn't).
- **P2 SRAM + NoC** — tensor-aware banking, placement, bit-mm metric; = Phase 4.5, the model's stated blind spot; could be negative.
- **P3 Dataflow A/B** — stationary vs streamed vs broadcast on exact shapes (= CHIP_ROADMAP gate 1); sets the bar P5/P5′ must beat.
- **P-V Low-voltage** — sub-V_min domains, droop scheduling; measured adverse on stock silicon; unlocked only by the test tile; never counted in bars.
- **P4-M1 Memory widening + compression** — 512-bit-class interface, weight-stream compression 62–83%, LPDDR6, PIM-for-KV (~1.1–1.4×).
- **P4-M2 3D integration** — hybrid-bonded stacked DRAM (8–16 GB over 100–200 MB SRAM; ledger-priced ×1.16 today; bank-local 1.3–2× [T]) AND vertical register-to-register operator pipelining across stacked compute tiers (3D-Flow-class, ~1.5× [X*, 7g]); thermal + supply kill questions open, shared by both halves.
- **P5 / P5′ Static substrate** — weight-resident CIM vs FixedWeight hardening, rivals for one slot; screened 1.19× / 1.28× over B1; ≥2× on the complete linear layer or the slot stays digital.
- **P6 Attention engine** — substrate-agnostic g_A, the load-bearing term in every study; screened 1.20× (CIM variant); success implies P4.
- **P7 Hybrid tile** — recombination of P5/P5′ + P6 winners; screened 1.48× central, Gen-3 band 6.0–9.7×; reopens on I1 macros.
- **P-W Workload levers** — Ledger B (certified reuse floors, tile attention, token merging, distillation); fenced: robot-measured quality only.
- **P-D Deterministic schedule & safety** — the guarantee project (= Phase 3): CFG hardware sharing, rolling-KV window, deterministic timing, miss-rate certification (Tier-3 + DRAM sim), thermal co-design, the flow-ODE/CEM update engine. Unlocks deployability, not a multiplier — which is why a rung-only map missed it (union check, 2026-08-17).

## Binding couplings (the branches are a partial order, not a menu)

1. **P6 ⇒ P4**: any pivot-grade compute gain goes memory-bound at the contract
   interface (~1.95× conversion cap, CIM study ideal row) — an attention breakthrough
   automatically promotes the memory program.
2. **P5 vs P5′**: rivals for one slot; the I1 three-macro run prices both at once.
3. **P3 → P5/P5′**: the dataflow winner is the bar the substrate branches must clear —
   CIM/hardening beat the *best* conventional implementation or nothing.
4. **P1 ↔ P2**: the fused schedule determines the traffic pattern banking must serve —
   separately attributable via the ledger, not physically independent.
5. **P4 content shifts under P5′**: hardening removes the weight half of 3D's absolute
   saving while the relative increment survives on the leaner total (tested,
   `tests/test_radical.py`).
6. **P-W is fenced**: quality-equivalence across model changes is UNSUPPORTED by the
   instrument; nothing from P-W enters a hardware ratio.

## What "done" looks like

Each project ends by moving its rung's number from [T] toward [P]/[M] grade — or by a
recorded kill. The ladder (WHITEPAPER table / simulation page) is the scoreboard; this
file is the map from ideas to rungs; the studies under `docs/generated/` are the
screens; `docs/review-audit.md` is the trail.
