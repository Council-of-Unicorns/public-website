# PROGRAM.md — the research program, one project per ladder rung

**Written 2026-08-17.** The division of every architecture idea in this repo into
separately attributable projects. Organizing principle: **each project is the unlock of
exactly one ladder rung, and its success criterion is that rung's multiplier** — so
attribution is automatic (the ledger separates the rungs), gates are inherited rather
than invented, and completeness is checkable: a project with no rung, or a rung with no
project, is visible instantly. Checked complete against the union of WHITEPAPER,
ETA_REPORT 7g/7g-bis, PERF_LEVERS, CHIP_ROADMAP, and the three studies (CIM, radical,
fixed-weight) on 2026-08-17.

Rule inherited from the studies: projects are **separate simulator branches evaluated
by one ledger** — never one architecture that accumulates every idea, and never
multiplied multipliers. Combined architectures are recomputed (S15/§22 discipline).

| Track | Project | Feeds which rung | Status / evidence | Gate |
|---|---|---|---|---|
| **Shared instruments** | | | | |
| | I0 — Ledger+ (add per-tensor lifetimes, bit-mm, energy Sankey) | all | ledger exists (`rpu/ledger.py`, every joule one category, tested); bit-mm and Sankey are the missing pieces (NoC is a stub) | none — it is the measuring instrument |
| | I1 — Measurement campaign (Thor bench @40 W, three-macro synthesis: FP4 tile + CIM macro + ROM/product-bank macro, PDK characterization, scaled FPGA) | all | sealed predictions registered before runs (`docs/PREDICTIONS.md` practice) | I1 **is** phase 0; prices every [T] below |
| **Baseline** (first silicon 2.9× → mature 4.2×) | | | | |
| | P-C — Compiler/extraction 0.55 → 0.80 (scheduling, tail fusion, DMA overlap, idle gating) | mature 4.2× | the four knobs are the ledger's software mechanisms; the largest committed multiplier | profiling vs FPGA + partner workloads |
| | P1 — Streaming transformer block (whole-block schedule, intermediates die at their consumer) | first silicon | fusion result exists (56.7× attention traffic, cycle model); block-level explicit schedule does not | bytes and pJ per block vs kernel-sequential |
| | P2 — SRAM + NoC (tensor-aware banking, producer→consumer placement, bit-mm metric) | first silicon → mature | = the already-roadmapped **Phase 4.5**, the model's stated blind spot; could be NEGATIVE | bit-mm/inference vs generic hierarchy |
| | P3 — Weight-reuse dataflow A/B (stationary vs streamed vs broadcast on exact shapes) | first silicon | = CHIP_ROADMAP gate-1 Timeloop comparison, already planned | MACs per fetched weight byte; sets the bar P5/P5′ must beat |
| **Gated upside** | | | | |
| | P-V — Low-voltage physical design (sub-V_min domains, droop scheduling, Razor-class margins) | the ×1.4 arm: 15.7× → 22× | measured ADVERSE on stock silicon (DVFS flat); requires custom design; never counted in bars | test-structure tile on the gate-4 shuttle |
| **Frontier** (≤ 20–44×, in escrow) | | | | |
| | P4-M1 — Conventional memory widening + compression (512-bit-class interface, many slow channels, lossless weight-stream compression 62–83%, LPDDR6, PIM-for-KV) | frontier (near arm) | 512-bit doubles ideal-compute realized speedup (CIM study crossover); 7g lever ~1.1–1.4× | roofline recomputation |
| | P4-M2 — 3D bank-local memory (hybrid-bonded stacked DRAM, 8–16 GB over 100–200 MB distributed SRAM, bank→SRAM→cluster) | frontier (far arm) | ledger-priced ×1.16 today (×1.11 repricing, ×1.04 static feedback); bank-local 1.3–2× is [T] | thermal + supply desk studies; Phase-4.5 mechanics; then ledger recomputation makes it THE ceiling |
| **Substrate branches** (Gen-2/Gen-3 tiers) | | | | |
| | P5 — Static weight-resident CIM **vs** P5′ — FixedWeight hardening (ROM/shared-product): RIVALS for one slot | Gen-2/Gen-3 | screened: P5 1.19×, P5′ 1.28× over B1 (P5′ also deletes weight memory; supersedes P5 in the Gen-3 lane) — `CIM_STUDY.md`, `FIXEDWEIGHT_STUDY.md` | the I1 macros; ≥2× on the complete linear layer or the slot stays digital |
| | P6 — Dynamic attention engine (substrate-agnostic: spatial QK→softmax→PV fabric, writable CIM, other) | Gen-2/Gen-3 — **the load-bearing term (g_A) in every study** | screened at 1.20× (CIM variant, central [T]); compared against the FUSED baseline, never naive attention | I1 macros + design study; success **implies P4** (every pivot-grade corner is memory-bound) |
| | P7 — Hybrid transformer tile (recombine P5/P5′ + P6 winners) | Gen-2/Gen-3 | screened at 1.48× central (`CIM_STUDY.md` CIM-Full); Gen-3 combined 6.0–9.7× band (`FIXEDWEIGHT_STUDY.md`) | reopens only on I1 macro results |
| **Fenced separate program** (quality-gated) | | | | |
| | P-W — Workload levers, Ledger B (cross-chunk reuse w/ certified floors, sliding-tile attention, token merging, step distillation) → model–silicon co-design | the horizon | PERF_LEVERS verdicts exist; gains Thor could also adopt cancel out of every hardware ratio | robot-measured quality, never simulator-only |

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
