# The simulators — a complete handoff

**Written 2026-08-10.** The definitive explainer for the project's modeling instruments:
what each one is, what question it answers, what it is calibrated against, what it may be
used for, and how the pieces check each other. Companions: `HANDOFF.md` (project-wide),
`SIM_REVIEW_HANDOFF.md` (the adversarial-review packaging), `ARCH_RESEARCH_HANDOFF.md`
(architecture research state).

Provenance tags: [M] measured by us · [S] simulator output · [X] literature, primary
opened · [X*] agent-relayed, primary not opened · [T] estimate/target.

---

## 0. The map

**Consolidated 2026-08-10 to two instruments plus a sweep layer** (see
`docs/generated/CONSOLIDATION_REPORT.md`): the mechanistic ledger's physics moved into
`rpu/ledger.py` as part of Simulator A. The A<->ledger disagreement was decomposed
exactly first — 68% overhead accounting, 32% software; the software-dominance hypothesis
was falsified. Completed 2026-08-13: the `rpu/codesign.py` compatibility shim is retired
(clients import `rpu.ledger` / `rpu.workload` directly), and the published scalar
identity has its own single home in `rpu/design_points.py`. The table below reflects the
consolidated state:

| Instrument | Lives in | Question it answers | Trust level |
|---|---|---|---|
| **Simulator A** — analytical roofline, calibrated | `rpu/` | Is the design feasible? Latency, energy, deadline-miss, η vs Thor | Calibrated to 4 measured anchors; predictive validity untested off-card |
| **Cycle model** — hermetic array/memory simulator | `sim/` | What does a given array geometry and schedule physically do? | Verified against SCALE-Sim + brute force; no energy or power model |
| **Mechanistic ledger path** (inside A) | `rpu/ledger.py` | Where does every joule go, across model x SRAM x software? | Structure sound, coefficients [T]; informs but does not set published numbers |
| **Published identity** (inside A) | `rpu/design_points.py` | The four-factor scalar accounting behind every published design point and the bounded-robust range | The headline source until the ledger is promoted (below) |
| **The explorer** — generated interactive page | `scripts/explorer_data.py` → `explorer.html` | Renders `design_points` + the bounded-robust range | Golden-checked at page load; authoritative rendering of the headline numbers |
| **CIM pivot evaluator** (added 2026-08-17) | `rpu/cim.py` → `scripts/cim_study.py` → `docs/generated/CIM_STUDY.md` | Should the compute substrate pivot to SRAM-CIM? Block-level dual-tile ledger, bundle-gain sweeps, memory crossover | [T] sweep coefficients; verdict CONTINUE DIGITAL (central R = 1.48); re-opens on the phase-0 tile measurement |
| **Radical-ASIC / FixedWeight evaluator** (added 2026-08-17) | `rpu/radical.py` → `scripts/radical_study.py` + `scripts/fixedweight_study.py` → RADICAL_STUDY.md + FIXEDWEIGHT_STUDY.md | Is a hardened-weight endpoint credible? Area gate, sequential-substitution ledger, ceilings, overlap vs CIM/3D, updateability regimes | [T] sweeps anchored on B1; verdicts: LONG-TERM STRETCH ~7–9x; FixedWeight INCLUDED as Gen-3 tier (central ~8x anchored, no published multiplier); 10x rejected as roadmap claim |

They deliberately do **not** share code. A and the cycle model agree on FLOPs to 0.7%
without any common implementation — that independence is the repo's strongest validation
artifact, and `tests/test_model_seam.py` guards the geometry both must be handed.

---

## 1. Simulator A (`rpu/`) — the calibrated analytical model

**The production instrument.** Every published number routes through it or through
constants it validated.

**Pipeline:** `WorkloadParams` (frozen 14B DiT shape; n_ctx derived, never typed) →
`workload.py` (the operator list per forward pass; CFG rule F2: compute ×2, weights+KV
once) → `roofline.py` (regime + weight residency, computed never assumed) → `latency.py`
(sensor-to-action stage chain, 20k-draw lognormal jitter MC, deadline-miss **rate** with
a 95% UCB that refuses to certify 1e-4 at insufficient samples) → `energy.py` (FLOP/byte
energies via the shared `UtilizationModel`; one `chunk_power` rule all callers import) →
`speedup.py` (the four-bound chunk time — the **energy cap** `E/(TDP·(1−f_static))`
binds at 40 W; S = η at power parity; η* by bisection) → `montecarlo.py` (feasibility
regions, sensitivity) → `report.py` (refuses authority if calibration fails).
`simb.py`/`jepa.py` are Simulator-B deltas — the generality argument — scored through
A's own `score_op`, never editing A's core (enforced by test).

**Calibration state, honestly:** four anchors, all measured on one 600 W RTX PRO 6000
[M], reproduced to 0.5–3.9% latency / 0.8–2.5% energy. But the anchors are power-capped,
so latency and energy are nearly one observation each: the Jacobian at the fit point has
singular values **4.995 / 2.437 / 0.021 / 0.00011 — the 4-parameter fit is effectively
rank 2** [S]. Two coefficients are pinned at bounds and printed UNIDENTIFIED; an
independent measurement (81.6% achieved bandwidth [M]) refutes one of them, and
`prediction_util()` states the prediction policy (measured bound over pinned artifact)
without altering the fit — the calibrated pipeline itself still reports the fit and
adopts the policy at the next re-fit, when goldens are re-pinned. Held-out validation lives in `fixtures/validation/`, which
the calibration loader **mechanically refuses** to fit on. A sealed Orin prediction
(59.1 ms / 2.68 J, `docs/PREDICTIONS.md`) awaits the board.

**What A produces:** the design points — **launch 2.88× / mature 4.19× / optimistic
11.0× / conservative 1.91×** vs Thor at 40 W (dense-FP4 semantics, NVIDIA primary [X]) —
and the **bounded-robust range 1.9–15.7×** (22× with gated physical design), the true
min/max over every input's defensible interval, corners proven by monotonicity.

**Known limits:** cross-architecture transfer untested (the Orin run is the test); the
compiler derate is the zero-gating corner (launch is a floor, band to 4.19×); stage-cost
fractions are structural guesses [T]; the fleet NoC is unmodeled (Phase 4.5).

## 2. The cycle model (`sim/`) — hermetic, geometric, energy-free

**Stdlib-only, Bazel-built, physically cannot import `rpu/`** — that isolation is
load-bearing (it is the substrate for RTL co-simulation later, and it is what makes the
cross-check meaningful).

**What it models:** `systolic.py` — the array identity `pass_cycles = S + rows + cols −
2`, verified exhaustively against a brute-force wavefront simulator sharing no code and
against SCALE-Sim, including non-square arrays that refute the rival closed form; partial
tiles drain through physical geometry; DMA overlap = max(compute, dma). `memory.py` —
tile schedules over loop orders against SRAM capacity, and `fused_attention_traffic`:
the 3120×18,720 score matrix (~233 MB/head/layer) never materializes; fusion is worth
**56.7×** on attention traffic [S]. `workload.py` — `simulate_forward_pass` as the
primitive; produced the geometry result (81.7% utilization @ 64×64 vs 44.4% @ 256×256,
mechanism fill/drain) — labeled *utilization optimum ignoring fleet interconnect*.

**What it deliberately lacks:** energy, power, jitter, calibration. It answers "how many
cycles and how many bytes," nothing else.

## 3. The seam between them — guarded, not merged

Both models are handed the same geometry, typed independently. `tests/test_model_seam.py`
asserts field-level equality and the **0.7% FLOP agreement**, and hosts the traffic
reconciliation: the scheduled cycle model moves **~4.9×** the fused analytical ideal
(band 1–10×, the honest width of the tiling model's ignorance; per-cause decomposition is
open review item #10). Merging the models would turn corroboration into tautology; the
seam tests are what make the split an asset.

## 4. The mechanistic ledger (`rpu/ledger.py`) — now part of Simulator A

**Consolidated into A** (2026-08-10; the `codesign.py` shim retired 2026-08-13), realizing the
external review's structural demand: **η as an output of an energy ledger, not an input.**

**The ledger:** `E_total = E_arith + E_reg_clock + E_control + E_SRAM + E_NoC + E_idle +
E_DRAM + E_static` — every joule in exactly one category (tested to 1e-12).
`f_datapath = E_arith/E_total` is **derived** (lands ~24% at the baseline — inside the
15–25% A assumes, a nontrivial consistency pass). Software enters as mechanisms
(utilization → time and gated idle energy; fusion quality → spill traffic; DMA overlap →
hiding) — never a divisor. Residency is a four-state taxonomy (external / package /
partial / full) decided by capacity + lifetime, with an under-provisioning spill penalty
and a [T]-gated package-memory tier that lowers pJ/B and charges time at a finite tier
bandwidth — it never deletes bytes. Physics corrected 2026-08-13 (external review, 10
findings): the residency planner now imports the workload's full L-layer KV footprint
(the local re-derivation dropped the layer factor and marked a ~1.3 GB cache resident in
1 GB), the DMA-overlap time formula respects both channel floors, and SRAM-resident KV
no longer pays stream-through buffering.

**What it found** (`docs/generated/CODESIGN_STUDY.md`, all [T]-coefficient): model size
dominates every objective, with a real **full-weight-residency phase transition at ≤1B
models + ~1 GB SRAM** (weight DRAM traffic → 0); SRAM is a **weak knob at the frozen
14B** (<4% energy swing across 32 MB–1 GB; the computed knee is ~96 MB, adjacent to the
chosen 90 MB); and it disagrees with A's software accounting by **~2.7×** on the same
baseline — the strongest argument for the ledger rebuild, and the reason neither number
quotes against the other until a measurement pins the gating factor.

**Status:** its η stays out of every headline. Its job is to justify and shape the
rebuild, and to locate which coefficient the model disagreement hinges on (it did: `g`,
the idle-gating fraction — measurable in the Orin profiling run).

## 5. Which numbers come from where

| Number | Source | Published? |
|---|---|---|
| Launch 2.88× / mature 4.19× / optimistic 11.0× / conservative 1.91× | A via the explorer generator | Yes — the design points |
| Bounded-robust range 1.9–15.7× (22× gated) | A, `eta_range()` over PARAM_BOXES | Yes — labeled interval arithmetic |
| Bar 2.0 / target 3.0 | Frozen contract (bench/contract.toml) | Yes — the 2.05/2.15 figures were derived eta* values, retired from headline use 2026-08-10 |
| Geometry 81.7%/44.4%; fusion 56.7×; pass-cycle identity | Cycle model | Yes — labeled [S] |
| Mode tables, feasibility regions, miss rates | A (calibrated) | Yes, with UCB resolution caveat |
| Ledger η ≈ 7.8, residency phase transition, SRAM knee | Co-design ledger | Report only — [T], not headline |

## 6. Operating it

```
bash scripts/check.sh                      # the whole gate: ruff, mypy, pytest, guards
bazel test //...                           # hermetic cycle-model suite alone
PYTHONPATH=. .venv/bin/python scripts/explorer_data.py   # regenerate the explorer page
PYTHONPATH=. .venv/bin/python scripts/codesign_study.py  # regenerate the co-design report
PYTHONPATH=. .venv/bin/python scripts/demo.py            # the sample feasibility report
```

Rules that keep it honest: generated artifacts are never hand-edited (L3); a physical
rule lives in one function (L14); every new test must be shown able to fail (L15);
subagent numbers are [X*] until a primary is opened (L10); fixtures/measured/ is program
input, fixtures/validation/ is fit-refused, fixtures/crosscheck/ stays out of the solver.

## 7. What would change everything

One measurement — **the Jetson Orin run** — now carries four payloads at once: it tests
whether A's calibration transfers across architectures (the sealed prediction), pins
Thor's side of every published ratio, prices the compiler gating factor that separates
A's 2.88 from the ledger's 7.8, and lands as the first entry in the fit-refused
validation directory. Every analytical route to sharpening the numbers has been run,
twice, plus an external review; the instruments are now waiting on physics.

## 8. The promotion plan (standing, decided 2026-08-13)

The architecture is converged in advance so that promoting the ledger to the published
accounting is **one edit, not a refactor**: the ledger is the only mechanistic physics
(shim retired), the scalar identity has one home (`rpu/design_points.py`), and
`rpu/reconcile.py` is the permanent bridge that names their disagreement. The switch —
re-deriving the published design points from `evaluate()` instead of `eval_point()` —
is **gated on the Orin measurement** pricing the idle-gating factor `g`, because the
ledger's coefficients are [T] and publishing them as headline before a measurement
arbitrates the 68% overhead share would trade a calibrated instrument for an
uncalibrated one. When the gate opens: swap the design-point source, re-pin the explorer
goldens, retire the reconciliation harness, and record the change here and in
`review-audit.md`.
