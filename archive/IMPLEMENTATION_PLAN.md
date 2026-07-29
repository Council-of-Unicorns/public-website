# IMPLEMENTATION_PLAN.md — FM-RPU Tier-1 Concept-Proving Simulator

> **STATUS: COMPLETE (2026-07).** Steps 0–11 all shipped; P1–P8 are green CI gates; the
> P6 calibration gate passed on measured RTX PRO 6000 anchors. This document is retained
> as the build record — unchecked boxes below are historical artifacts of the plan
> format, not open work. Current work lives in `CHIP_ROADMAP.md`.

Derived from [`docs/system-design.md`](system-design.md) (the locked design). This plan
sequences the build of **Simulator A** (DreamZero-specialized) and then **Simulator B**
(DreamZero + JEPA, as deltas on A), at **Tier 1** fidelity (analytical roofline + memory
traffic).

## Pre-flight recommendation: **build from scratch** (greenfield)

The repo is empty except docs + skill wiring. There is no aligned code to migrate and
nothing that violates doctrine yet. So this is a **build sequence**, not a migration.

- **Already aligned:** nothing (empty repo).
- **To be excised later:** nothing (no legacy).
- **Language/stack:** Python 3.11+, `numpy`/`scipy` for the roofline + Monte Carlo,
  `pytest` + `hypothesis` for tests, `ruff` + `mypy --strict` as the static gate. Rationale:
  the instrument is arithmetic over small parameter sets; correctness and reproducibility
  dominate, raw speed does not (the MC is embarrassingly parallel and small).
- **The one hard external dependency:** the *measured anchor data* (§0.1–0.2 — your B200
  3-step DreamZero fork, a Thor/Orin point, DreamZero public anchors). The simulator cannot
  invent these; no FM-RPU result is trustworthy until they're supplied and reproduced. See
  **§D1**. Until they exist, only clearly-flagged synthetic fixtures exercise the pipeline.

---

## The steps at a glance

- [ ] **Step 0 — Foundation.** Package skeleton, pytest/ruff/mypy, CI, determinism harness, `results/results.tsv` logger. *Test infra only.*
- [ ] **Step 1 — Lock the contract.** `params.py` (WorkloadParams, HardwareRow, UtilizationModel — all frozen), `opcost.py` (`OpCost`), a stub operator + stub row proving pluggability. Lands P1-scaffold, P8-determinism, schema round-trip.
- [ ] **Step 2 — First vertical slice: one operator on one row.** FFN → roofline → (time, energy, regime). Lands P5, P2 (for one op).
- [ ] **Step 3 — Second vertical slice: full DreamZero forward on all three rows.** All operators incl. video-latent tokens, KV over the 2 s window, weight-stationary CFG reuse; full A4 latency loop + A5 energy. Lands P1, P2, P3, P4.
- [ ] **Step 4 — Calibration + the golden path.** A6.1–2 anchor reproduction, fit of `e_byte`/utilization, the **< 15%** gate. Lands P6. Golden path (§A) goes live.
- [ ] **Step 5 — Thermal sub-model.** Neck-path steady-state ΔT + sustained-power ceiling flag. *(Parallel after Step 3.)*
- [ ] **Step 6 — Monte Carlo + confidence bands + sensitivity ranking.** A6.4. Lands P7.
- [ ] **Step 7 — Design-space sweep.** Feasibility map, Thor 273 GB/s wall, min-viable-spec frontier, B200-at-head-power ratio (A8); adversarial baseline (A6.3) as a gate.
- [ ] **Step 8 — Simulator B (deltas only).** JEPA workload generator, reuse-axis width, programmable-update-engine cost, union provisioning point, A-vs-B gap, Part-C tier-collapse check. Lands P8-isolation.
- [ ] **Step 9 — CI guards + failure injection.** Freeze P1–P8 as merge gates. *(After Step 8; must not precede it or main goes red.)*
- [ ] **Step 10 — Reporting / observability.** Feasibility report artifact + sensitivity output. *(Parallel, anytime after Step 6.)*
- [x] **Step 11 — Success metric: speedup vs Thor (A8a), 2× = success.** `fmrpu/speedup.py`: power-capped chunk time (both rows, one formula — P1), speedup as a region with `P(S≥2)` (P7), `required_efficiency_advantage` (η\*, the D7-labeled etch-efficiency input, DUT-only, never folded into the η=1 headline), FP16→FP4 energy-scaling `s` as an MC input pending an FP8/FP4 anchor. Proved by `tests/test_speedup.py` (region shape, identical-rows S=1, TDP-ratio identity under dual power-limit, uncapped peak-ratio tracking, η\* flips success, η never leaks into the baseline, determinism). Readout: `scripts/speedup_readout.py` (P6-gated on the measured-anchor calibration).

### Dependency graph

```
0 ──▶ 1 ──▶ 2 ──▶ 3 ─┬─▶ 4 ──▶ 6 ──▶ 7 ──▶ 8 ──▶ 9
                     ├─▶ 5 (parallel)
                     └─▶ 10 ◀── 6 (parallel)
```

Critical path: **0 → 1 → 2 → 3 → 4 → 6 → 7 → 8 → 9.** Steps 5 and 10 are parallel.

---

## Properties to preserve (gates, not aspirations)

### P1 — Fairness: one utilization model, applied to every hardware row
**Invariant:** every hardware row is scored through one identical `UtilizationModel`; the core (`roofline.py`, `latency.py`, `energy.py`, `thermal.py`) is **row-agnostic**.
**Forbids:** any hardware-row name literal (`thor`, `b200`, `fm-rpu`, `fmrpu`) inside the core modules; any per-row utilization override; granting the design-under-test ideal utilization while baselines get realized numbers.
**Allowed:** rows differing only in their *data* (`HardwareRow` fields); one utilization model *fit from measurement* (Step 4) shared by all.
**Proved by:** Step 3 (`test_fairness.py`) + Step 9 CI grep guard.

### P2 — KV traffic is a first-class term
**Invariant:** `bytes_KV` is computed per operator and included in every latency/energy total; byte accounting is complete (`total_bytes == weight + KV + act`, no term silently dropped).
**Forbids:** any total that sums only `weight_bytes`; dropping KV at long horizon.
**Allowed:** `act_bytes ≈ 0` for fused ops (must still be an explicit 0, not omitted).
**Proved by:** Step 2 (accounting completeness) + Step 3 (`test_kv_first_class.py`: at the 2 s / ~18.7k-token default, `bytes_KV` is ≥ 10% of total traffic — a first-class term, not a rounding error).

### P3 — 14B weights are never SRAM-resident at head power
**Invariant:** the residency classifier returns *stream-every-step* whenever `working_set > SRAM_capacity`; for 14B @ 4-bit (≈ 7 GB) against any head-power SRAM (≤ a few GB) it must classify HBM-weight-streaming per step.
**Forbids:** a code path that amortizes 14B weights into SRAM under head-power capacity.
**Proved by:** Step 3 (`test_weight_residency.py`).

### P4 — The video branch runs even with no pixel output
**Invariant:** `drop_pixel_decoder=True` removes **only** the VAE-decode operator; the video-latent tokens still flow through every DiT operator.
**Forbids:** modeling "no pixels" as a large FLOP/byte drop; excluding video-latent tokens from `N`.
**Proved by:** Step 3 (`test_video_without_pixels.py`: FLOPs(no-decode) == FLOPs(with-decode) − FLOPs(decode op only), and that delta is < 2% of the forward).

### P5 — Roofline regime is a computed output, not an assumption
**Invariant:** compute-bound vs bandwidth-bound (weight-BW / KV-BW) is derived from each operator's arithmetic intensity vs the row's ridge point.
**Forbids:** any hardcoded regime label; branching on workload *name* to pick a regime.
**Proved by:** Step 2 (`test_roofline_regime.py`: synthetic op below ridge → bandwidth-bound, above → compute-bound; the sweep finds the crossover).

### P6 — Measurement-first: no extrapolation without a passing calibration gate
**Invariant:** an FM-RPU (un-built row) feasibility result is emitted **only** if the calibration anchors reproduce measured latency **and** energy within the stated tolerance (default < 15%).
**Forbids:** returning any FM-RPU feasibility when the calibration gate is red or anchors are missing — must raise a visible, named error, not silently proceed.
**Proved by:** Step 4 (`test_calibration_gate.py`: a deliberately mis-fit `e_byte` fails the gate and blocks FM-RPU output).

### P7 — Feasibility is a region with confidence bands, never a point
**Invariant:** every feasibility answer carries a Monte-Carlo distribution (quantiles / confidence band) over the load-bearing uncertain inputs plus a sensitivity ranking.
**Forbids:** any public API returning a scalar `feasible: bool` (or a single latency/energy) without an attached uncertainty band.
**Proved by:** Step 6 (`test_region_not_point.py`).

### P8 — Determinism, and B is isolated from A
**Invariant:** (a) same inputs + same seed → byte-identical results; (b) the presence of Simulator-B code does not change any Simulator-A (DreamZero) result — computing the DreamZero feasibility via the B codebase is byte-identical to A.
**Forbids:** wall-clock/`random`-without-seed nondeterminism; B editing A's core to fit JEPA (deltas only).
**Proved by:** Step 1 (determinism) + Step 8 (`test_b_isolation.py`) + Step 9 CI guard (core modules unchanged by B).

> Property calibration: 8 invariants, each with a named test in a named step. Anything not
> on this list is taste, handled by `principal-production-engineer` / `python-style` during
> review — not a merge gate here.

---

## How to execute

- **Contract first.** Step 1 locks `params.py` + `opcost.py`. Nothing downstream starts until they typecheck under `mypy --strict`.
- **One capability end-to-end per step.** A slice runs *params → workload → roofline → number* and leaves the instrument working. No "build all operators, then wire the totals" mega-step.
- **Tests first, structurally.** The "Tests first" block precedes "Implementation" in every step. Coding agents write the failing test, watch it fail for the right reason, then implement.
- **Acceptance is binary.** A grep that returns empty, a test that is green, a golden file that matches, a number within tolerance. No "looks right."
- **Delete-after-verify.** Any removal lives in the step's Acceptance block, gated by that step's tests passing.
- **Rewrite-from-scratch is allowed** (and often faster than untangling a stuck module) — the gate is the test, not the provenance of the code. Note the chosen path in the PR body.
- **Properties are merge gates.** A step that demonstrably weakens P1–P8 cannot merge.
- Follow the iteration loop in **§B** when a test is red; stuck > 30 min → escalate in the PR, do not start the next step.

---

## Step 0 — Foundation

**Goal:** an empty but fully-gated Python package that runs `pytest`, `ruff`, `mypy --strict` green in CI, with a determinism harness and an append-only results log.
**Why now:** every later step's acceptance is "a test is green in CI." That machinery must exist first, or acceptance gates are unverifiable.

### Tests first
- [ ] `tests/test_smoke.py` — imports the `fmrpu` package; asserts version string. (Proves the harness runs.)
- [ ] `tests/conftest.py` — a `deterministic_rng(seed)` fixture used everywhere randomness appears; a `assert_byte_identical(a, b)` helper (canonicalize floats to a fixed decimal, compare).

### Implementation
- [ ] `fmrpu/__init__.py` (package + `__version__`), `pyproject.toml` (deps: numpy, scipy, hypothesis; dev: pytest, ruff, mypy), `ruff.toml` (select `E,F,B,SIM,RET,TRY,BLE,PLC0415,C901`), `mypy` strict config.
- [ ] `fmrpu/resultlog.py` — append-only TSV writer to `results/results.tsv` (one row per evaluated config; header stamped; idempotent open-append).
- [ ] `.github/workflows/ci.yml` (or `scripts/check.sh` if no GH runner) that runs ruff + mypy + pytest and exits non-zero on any failure.

### Integration check
- [ ] `scripts/check.sh` exits 0 on a clean checkout.

### Acceptance
- [ ] `ruff check . && mypy --strict fmrpu && pytest -q` all exit 0.
- [ ] `grep -rn "random\." fmrpu/ | grep -v "default_rng"` returns empty (no unseeded randomness).
- [ ] `results/results.tsv` is created and appended idempotently (run the logger twice → 2 rows, header once).

**Depends on:** nothing.

---

## Step 1 — Lock the contract

**Goal:** frozen parameter/schema types (`WorkloadParams`, `HardwareRow`, `UtilizationModel`, `OpCost`) and a stub operator + stub hardware row that prove new operators/rows plug in without touching dispatchers.
**Why now:** the per-operator `OpCost` tuple and the row schema are the interfaces every model in A and B speaks. Contract first; nothing else compiles without it.
**Note:** the fairness (P1) *test* needs multiple rows + the shared utilization model, which only fully exist by Step 3; here we land the schema round-trip, pluggability, and determinism scaffolds only — no forward references (Pitfall 1).

### Tests first
- [ ] `tests/test_schema.py` — round-trip each frozen dataclass (construct → serialize → construct) is byte-identical; all fields are typed; `HardwareRow` carries `{fp4_peak, hbm_bw, hbm_capacity, sram_capacity, sram_bw, dequant_tput, attn_engine_tput, interconnect_bw, fixed_op_overhead, tdp}` (A3) and **no** utilization fields (utilization lives in `UtilizationModel`, shared — P1).
- [ ] `tests/test_pluggability.py` — register a `StubOperator` via the operator registry; assert it appears in the emitted `list[OpCost]` without editing any dispatcher; register a `StubRow`; assert it scores without special-casing.
- [ ] `tests/test_determinism.py` — build params from a seed twice → byte-identical (P8a).

### Implementation
- [ ] `fmrpu/opcost.py` — `OpCost(name, flops, weight_bytes, act_bytes, kv_bytes, precision)` frozen; a `total_bytes` property = `weight+act+kv` (P2 completeness lives in the type).
- [ ] `fmrpu/params.py` — the three frozen dataclasses; `WorkloadParams` defaults from A1 (P=14e9, d=5120, L=40, ffn=13824, heads=40, res 480×832, 1560 tok/frame, horizon 2.0s, N_ctx≈18.7k, steps=3, control_period=200ms, w_bytes for 4-bit, a_bytes for FP8/FP16). `UtilizationModel` holds `{compute_util, bw_util, overlap_factor, e_flop(precision), e_byte(tier)}` — the *only* place utilization lives.
- [ ] `fmrpu/registry.py` — operator registry (name → emitter) enabling per-op pluggability.

### Integration check
- [ ] Golden path (§A) is defined but **skipped** with a clear reason (`needs Step 4 calibration`); CI shows it as skipped, not failing.

### Acceptance
- [ ] `mypy --strict` green; every field on the three dataclasses is typed.
- [ ] `grep -rniE "thor|b200|fm.?rpu" fmrpu/roofline.py fmrpu/latency.py fmrpu/energy.py 2>/dev/null` — files may not exist yet; when they do (Steps 2–3) this must return empty (P1). Add the grep to `scripts/check.sh` now so it guards from first appearance.
- [ ] `test_schema.py`, `test_pluggability.py`, `test_determinism.py` green.

**Depends on:** Step 0.

---

## Step 2 — First vertical slice: one operator on one row

**Goal:** the simplest end-to-end path — an FFN operator's `OpCost` → roofline → `(time, energy, regime)` on a single `HardwareRow` — proving the pipeline shape.
**Why now:** proves *params → workload → roofline → number* with minimum complexity before the full forward piles on invariants.

### Tests first
- [ ] `tests/test_roofline_regime.py` (P5) — a synthetic op with arithmetic intensity below the row's ridge point classifies `bandwidth-bound`; above → `compute-bound`; exactly at → documented tie-break. A sweep of intensity finds the crossover within one grid step.
- [ ] `tests/test_op_accounting.py` (P2, single op) — for the FFN op, `time = max(flops/effective_compute, total_bytes/effective_bw) + fixed_overhead`; `energy = flops·e_flop + total_bytes·e_byte`; and `total_bytes` includes every non-zero term.
- [ ] `tests/test_energy_units.py` (F1 — the 8× landmine) — `e_byte` is stored and consumed in **pJ/byte**; a helper `pj_per_bit_to_pj_per_byte(x) == 8·x` is used at every datasheet-ingestion point; assert the HBM3e default rounds to ~20 pJ/byte (≈2.5 pJ/bit), not 30–40; assert `e_flop`/`e_byte`/bandwidth units compose to seconds and joules (dimensional check on a known hand calc).

### Implementation
- [ ] `fmrpu/workload.py` — FFN emitter only: `FLOPs_matmul = 2·P_active·N_new`, `weight_bytes = P_active·w_bytes`, `kv_bytes=0` for FFN, `act_bytes` tiled estimate.
- [ ] `fmrpu/roofline.py` — `score_op(op: OpCost, row: HardwareRow, util: UtilizationModel) -> OpResult(time, energy, regime, intensity)`. Row-agnostic (P1). Regime from intensity vs ridge `= effective_compute / effective_bw`.

### Integration check
- [ ] Run FFN on one hand-built row; print `(time, energy, regime, intensity)`; sanity-check the regime against a hand calc (leave a comment with the arithmetic).

### Acceptance
- [ ] `test_roofline_regime.py`, `test_op_accounting.py` green.
- [ ] `grep -rniE "thor|b200|fm.?rpu" fmrpu/roofline.py` returns empty (P1).
- [ ] `grep -rniE "bandwidth.?bound|compute.?bound" fmrpu/ | grep -v "roofline.py"` returns empty — regime label is produced in exactly one place, never hardcoded elsewhere (P5).

**Depends on:** Step 1.

---

## Step 3 — Second vertical slice: full DreamZero forward on all three rows

**Goal:** the complete Tier-1 Simulator-A forward — every operator (VAE encode, patch embed, per-layer {QKV, self-attn, out proj, cross-attn, FFN}, flow update, action head), video-latent tokens included, KV over the full 2 s window, weight-stationary CFG reuse — run through the A4 latency loop and A5 energy, scored on **Thor, B200, and one FM-RPU sweep row** under one utilization model.
**Why now:** this is the most-complex slice and carries the most invariants; landing it here proves the doctrine on the hard case. Everything after is calibration, uncertainty, and B.
**Note:** FM-RPU numbers here are **not yet trustworthy** — they become so only after Step 4's calibration gate. This step proves *structure*, Step 4 proves *fidelity*.

### Tests first
- [ ] `tests/test_fairness.py` (P1) — score all three rows; assert the *same* `UtilizationModel` object reference reaches every row; property test (hypothesis): permuting row order and re-scoring yields identical per-row results (no cross-row state).
- [ ] `tests/test_kv_first_class.py` (P2) — at default 2 s / N_ctx≈18.7k, `sum(kv_bytes) / sum(total_bytes) ≥ 0.10` (expected ≈ **0.4–0.5** — computed `2·N_ctx·L·d·a_bytes ≈ 7.6 GB` ≈ the 7 GB weight term, so this is a conservative floor, not a target); and dropping the KV term changes total latency on at least one row by > 5% (it is load-bearing).
- [ ] `tests/test_weight_residency.py` (P3) — `residency(working_set=7GB, sram≤4GB) == STREAM_PER_STEP`; with `sram ≥ working_set` → `STREAM_PER_CHUNK`.
- [ ] `tests/test_video_without_pixels.py` (P4) — `flops(drop_pixel_decoder=True) == flops(False) − flops(vae_decode_op)`, and that delta < 2% of the forward.
- [ ] `tests/test_cfg_reuse.py` (F2) — **both** `bytes_weight` **and** `bytes_KV` are fetched once per *step* and shared across the CFG pair (÷2 vs per-forward), because the context KV is identical for both branches; assert KV is not double-counted per forward (would inflate the binding bandwidth term ~+50%). In the distilled batch-1 path (no CFG), there is no pair to share across.
- [ ] `tests/test_energy_dominance_is_output.py` (F4, parallel to P5) — the byte-vs-FLOP energy split is an **emitted output** (`EnergyBreakdown{byte_energy, flop_energy, byte_fraction}`), not a hardcoded assumption; assert `byte_fraction` is computed from the actual traffic and precision, and that "HBM byte energy dominates" is reported as a *result* of the default config, not asserted a priori.

### Implementation
- [ ] `fmrpu/workload.py` — all operators per A1/A2; `N` includes video-latent tokens; `FLOPs_attn = 4·L·N_new·N_ctx·d`; `bytes_KV = 2·N_ctx·L·d·a_bytes`; **weight *and* context-KV stationary across the CFG pair** (both ÷2 vs per-forward — F2); `drop_pixel_decoder` removes only the decode emitter.
- [ ] `fmrpu/roofline.py` — residency classifier (`working_set` vs `sram_capacity`) driving per-step vs per-chunk streaming.
- [ ] `fmrpu/latency.py` — A4 loop `capture→ISP→VAE→prefill→[steps×(CFG DiT over N_new attending N_ctx)→flow]→action→emit`; per-stage `t = max(compute, mem) + overhead` with overlap factor; returns p50, p99.9 under a jitter model, and deadline-miss-rate vs the 200 ms period.
- [ ] `fmrpu/energy.py` — A5 `Energy = Σ flops·e_flop + Σ bytes·e_byte`; returns an `EnergyBreakdown` (byte vs FLOP split, `byte_fraction`) so dominance is an emitted output (F4); avg/peak power, energy/chunk.

### Integration check
- [ ] Emit a per-operator `(FLOPs, weight_bytes, act_bytes, kv_bytes, time, energy, regime)` table for the default config on each row; log to `results/results.tsv`. Eyeball that the bottleneck operator differs between short- and long-horizon configs (the crossover A2 predicts).

### Acceptance
- [ ] P1–P4 tests + `test_cfg_reuse.py` (F2) + `test_energy_units.py` (F1) + `test_energy_dominance_is_output.py` (F4) green.
- [ ] `grep -rniE "thor|b200|fm.?rpu" fmrpu/{roofline,latency,energy,workload}.py` returns empty (P1) — rows are data, not code.
- [ ] `grep -rniE "pj_per_b(it|yte)|e_byte" fmrpu/params.py` shows `e_byte` carries an explicit pJ/byte unit and the datasheet ingestion converts from pJ/bit (F1).
- [ ] Deadline-miss-rate is reported as a rate (a float in [0,1]), never a boolean; `grep -rn "def .*deadline" fmrpu/latency.py` shows a rate return type.

**Depends on:** Step 2.

---

## Step 4 — Calibration + the golden path

**Goal:** fit `e_byte` and the utilization model against **measured anchors**, reproduce your B200 3-step DreamZero fork + a Thor/Orin point + DreamZero public anchors within tolerance (default < 15% on latency **and** energy), and gate all FM-RPU extrapolation on that reproduction (P6).
**Why now:** this is the "measurement-first" contract (§0). Before it passes, no FM-RPU feasibility claim is valid; after it, the golden path (§A) is live and runs on every subsequent step.
**Note:** requires **user-supplied** anchor fixtures (see §D1). Until real data lands, `fixtures/anchors/*.json` hold clearly-marked `"authoritative": false` synthetic values used only to exercise the pipeline; the gate treats non-authoritative anchors as *not calibrated* and blocks FM-RPU output exactly as if they were missing.

### Tests first
- [ ] `tests/test_calibration_gate.py` (P6) — with a deliberately wrong `e_byte`, `reproduce_anchors()` reports error > tolerance and `feasibility(fmrpu_row)` raises `CalibrationNotPassed` (named, visible); with anchors within tolerance, it proceeds.
- [ ] `tests/test_calibration_crossval.py` (§D4) — fit on the B200 anchor, hold out the Thor anchor; assert held-out reproduction error < tolerance (guards overfitting to one memory system).
- [ ] `tests/test_golden_path.py` (§A) — full pipeline on the committed B200 anchor fixture reproduces measured latency & energy within 15%, and the result object matches the stamped golden file after float canonicalization.

### Implementation
- [ ] `fmrpu/calibrate.py` — `reproduce_anchors(anchors) -> AnchorReport` (modeled vs measured, per-anchor error); a bounded fit of `{e_byte, compute_util, bw_util, overlap_factor}` (scipy least-squares) constrained to physical ranges; `calibrated_envelope` (min/max of anchor inputs) — extrapolation flagged when a query leaves it.
- [ ] `fmrpu/params.py` — `CalibrationNotPassed` exception; feasibility entry points require a passed `CalibrationReport` handle (type-enforced, not a flag).
- [ ] `fixtures/anchors/{b200_dreamzero_3step,thor_point,dreamzero_public}.json` (schema + non-authoritative placeholders); `fixtures/golden/b200_dreamzero_3step.json`.

### Integration check
- [ ] Golden path green (un-skip it from Step 1). It now runs after every later step.

### Acceptance
- [ ] P6 test + cross-val + golden-path tests green.
- [ ] `grep -rn "feasib" fmrpu/ | grep -i "fmrpu\|rpu"` shows every FM-RPU feasibility path takes a `CalibrationReport` argument (no un-gated extrapolation).
- [ ] Anchor fixtures with `"authoritative": false` cause `feasibility(fmrpu_row)` to raise — verified by a test.

**Depends on:** Step 3.

---

## Step 5 — Thermal sub-model *(parallel after Step 3)*

**Goal:** steady-state neck-path thermal transport (junction → vapor chamber → neck conductance → torso radiator), reporting the sustained-power ceiling the fanless head can reject and flagging any compute point that exceeds it.
**Why now:** §A5 makes thermal part of the proof, not an afterthought — the binding constraint may be heat rejection through the neck, not the battery. Independent of calibration, so parallelizable.

### Tests first
- [ ] `tests/test_thermal.py` — for a given per-stage conductance chain and ambient, `sustained_ceiling_w` solves `ΔT_junction = P · Σ R_thermal`; a point above the ceiling sets `thermal_limited=True`; monotonicity: higher neck conductance → higher ceiling (hypothesis).

### Implementation
- [ ] `fmrpu/thermal.py` — resistance-network steady-state solve; inputs are `HardwareRow.tdp` + a `ThermalPath` param block; output `{sustained_ceiling_w, junction_dT, thermal_limited}`. Row-agnostic (P1).

### Integration check
- [ ] Feed Step 3's peak/avg power into the thermal model for the default FM-RPU row; report whether the neck path carries it.

### Acceptance
- [ ] `test_thermal.py` green; `grep -rniE "thor|b200|fm.?rpu" fmrpu/thermal.py` empty (P1).
- [ ] Latency/energy results now carry a `thermal_limited` flag alongside the deadline-miss-rate.

**Depends on:** Step 3.

---

## Step 6 — Monte Carlo + confidence bands + sensitivity

**Goal:** propagate the load-bearing uncertain inputs (realized BW utilization, `e_byte`, tokens/frame, distillation/step ceiling) through the calibrated model to produce a **feasibility region with confidence bands** and a **sensitivity ranking** (A6.4).
**Why now:** §0.3 forbids single-point feasibility; this is where P7 becomes real. Requires the calibrated model (Step 4).

### Tests first
- [ ] `tests/test_region_not_point.py` (P7) — the public `feasibility()` returns a `FeasibilityRegion{quantiles, ci_low, ci_high, samples}` with `samples > 1`; a static-analysis test asserts no public function is annotated to return a bare `bool`/`float` feasibility.
- [ ] `tests/test_sensitivity.py` — with one input's variance zeroed, its sensitivity rank drops to last; the two expected load-bearing inputs (realized BW utilization; step/horizon-compression ceiling) can be recovered as top-ranked on a synthetic model where they are wired to dominate.
- [ ] `tests/test_mc_determinism.py` (P8a) — same seed → byte-identical MC output.

### Implementation
- [ ] `fmrpu/montecarlo.py` — seeded sampler over declared input distributions; `FeasibilityRegion` with quantiles + CI; Sobol/one-at-a-time sensitivity ranking; append each draw's summary to `results/results.tsv`.

### Integration check
- [ ] Produce the DreamZero feasibility region for the default FM-RPU sweep point; golden path still green.

### Acceptance
- [ ] P7 + sensitivity + MC-determinism tests green.
- [ ] `grep -rnE "-> *bool" fmrpu/ | grep -i feasib` returns empty (no point-estimate feasibility API, P7).

**Depends on:** Step 4.

---

## Step 7 — Design-space sweep (the actual proof outputs)

**Goal:** sweep (horizon, steps, tokens, precision, chip params) to emit A8's deliverables — the feasibility map, the **bandwidth-vs-compute crossover** at 5 Hz @ 2 s, the **minimum-viable-spec frontier** (HBM GB/s, FP4 TFLOPS, SRAM MB, W) that clears 200 ms at ≤ 35 W, **where Thor's 273 GB/s wall falls**, and the speedup/energy ratio vs a B200 held to head power — with the adversarial baseline (A6.3) applied.
**Why now:** this is what Simulator A exists to produce; it needs calibrated MC (Step 6).

### Tests first
- [ ] `tests/test_adversarial_baseline.py` (A6.3) — Thor and B200 evaluated at their *best case* (max distillation/batching) still under the one shared utilization model; the FM-RPU frontier is reported relative to those best cases, not weakened baselines.
- [ ] `tests/test_thor_wall.py` — on a synthetic sweep where bandwidth is the binding term, the frontier identifies the BW below which the deadline is missed; Thor's 273 GB/s sits on the miss side for the default 14B/2 s workload (given calibrated inputs).
- [ ] `tests/test_min_viable_spec.py` — the emitted frontier is the Pareto boundary of {clears 200 ms ∧ ≤ 35 W ∧ miss-rate ≤ target}; a point just inside is feasible, just outside is not.

### Implementation
- [ ] `fmrpu/sweep.py` — grid/adaptive sweep over the design space; Pareto frontier extraction; Thor-wall locator; B200-at-head-power comparison; adversarial-baseline harness.

### Integration check
- [ ] Emit the feasibility map + frontier for the default DreamZero workload to `results/` and log summary rows.

### Acceptance
- [ ] Adversarial, Thor-wall, min-viable-spec tests green.
- [ ] Every emitted feasibility point carries confidence bands (P7) and a `thermal_limited` flag (Step 5) — grep the report schema.

**Depends on:** Step 6 (and Step 5 for the thermal flag).

---

## Step 8 — Simulator B (DreamZero + JEPA), deltas only

**Goal:** add a JEPA workload generator + the reuse-axis abstraction + a programmable-update-engine cost, find the single **union provisioning point** that clears 5 Hz @ 2 s in *both* modes, measure the A-vs-B perf/watt gap on the DreamZero workload, and check the Part-C tier-collapse condition — **without editing A's roofline/hardware/latency/thermal/calibration core** (P8b).
**Why now:** B is the hedge, defined as deltas on a proven A. Building it last makes "B is deltas on A" a checkable claim rather than an aspiration.

### Tests first
- [ ] `tests/test_b_isolation.py` (P8b) — computing the DreamZero feasibility via the Simulator-B code path is **byte-identical** to Simulator A (adding JEPA doesn't perturb DreamZero); property test over configs.
- [ ] `tests/test_reuse_axis.py` (B2) — the same roofline equations, parameterized by reuse-axis width, classify diffusion (CFG pair ≈ 2, low batch) as **bandwidth-bound** and JEPA-MPC (M≈hundreds) as **compute-bound**. Same code, opposite regimes.
- [ ] `tests/test_union_point.py` (B3) — the union provisioning point satisfies **both** the bandwidth floor (low-batch diffusion) and the compute headroom (MPC batch); a point that clears only one mode is rejected.
- [ ] `tests/test_part_c_tier_collapse.py` (C4) — at 14B/4-bit (7 GB) both families classify weights as HBM-streamed (no SRAM-resident tier to collapse) → predicted A-vs-B gap is single-digit %; at a synthetic ~1–3B model whose working set fits SRAM, the DreamZero-only design collapses a memory tier and the gap becomes large (the condition that would break the thesis is *detected*, not assumed away).
- [ ] `tests/test_jepa_size_swept.py` (F3 — thesis-critical) — the JEPA predictor size is a **swept input**, never hardcoded to 14B. Assert (a) the union point and the A-vs-B DreamZero gap are recomputed across a JEPA-size grid that **includes the empirically-real 1–2B point** (V-JEPA 2 ≈ 1.2B), and (b) at a small-JEPA point the reported over-provisioning leakage is priced from the actual `(JEPA_params × M × H)` compute headroom and the actual JEPA residency regime — not assumed equal to the 14B core. `grep -rn "14e9\|14B" fmrpu/jepa.py` returns empty (JEPA size comes from params, not a literal).

### Implementation
- [ ] `fmrpu/jepa.py` — JEPA workload generator (frozen-ViT encode-once + predictor rollout tokens; **predictor param count is a swept parameter, default ~1.2B per V-JEPA 2, not the 14B core** — F3; batch axis M, horizon H) reusing the **identical** `OpCost` emitter.
- [ ] `fmrpu/update_engine.py` — programmable-update-engine area/energy cost (a few % of the matmul/attn datapath) running flow-ODE *or* CEM.
- [ ] `fmrpu/roofline.py` — extend **by parameter only** (reuse-axis width); no row/name special-casing. `fmrpu/latency.py` — swap the inner loop via a strategy passed in, not by editing the loop for JEPA.
- [ ] `fmrpu/sweep.py` — union-point search + A-vs-B gap on the DreamZero workload.

### Integration check
- [ ] Report the A-vs-B DreamZero perf/watt gap with confidence bands; golden path (DreamZero, Simulator A) still byte-identical.

### Acceptance
- [ ] All Step-8 tests green.
- [ ] **P8b core-freeze guard:** `git diff --stat <step7-tag> -- fmrpu/roofline.py fmrpu/latency.py fmrpu/energy.py fmrpu/thermal.py fmrpu/calibrate.py` shows only *additive parameterization* (no branch on workload name); a test asserts the JEPA path imports the core, never monkeypatches it.
- [ ] The Part-C gap is emitted as a region (P7), and the tier-collapse condition is a reported check, not a hardcoded conclusion.
- [ ] `test_jepa_size_swept.py` (F3) green; `grep -rn "14e9\|= *14B" fmrpu/jepa.py` returns empty.

**Depends on:** Step 7.

---

## Step 9 — CI guards + failure injection

**Goal:** freeze P1–P8 as merge gates so regressions can't land.
**Why now:** guards come *after* the behaviors they protect exist (Steps 2–8), or main goes red on merge (ordering rule).

### Tests first / Implementation
- [ ] Add to `scripts/check.sh` / CI: the P1 row-name grep over all core modules; the P7 `-> bool` feasibility grep; the P8b core-freeze diff check; run the full property suite.
- [ ] `tests/test_failure_injection.py` — inject (a) a NaN-emitting operator, (b) a missing anchor, (c) an FM-RPU query outside the calibrated envelope; assert each produces a **named, visible failure** (not a silent fallback): NaN → raised, missing anchor → `CalibrationNotPassed`, out-of-envelope → flagged extrapolation warning attached to the result.

### Acceptance
- [ ] CI fails if any P1–P8 guard is violated (verify by temporarily breaking one and seeing red, then revert).
- [ ] `test_failure_injection.py` green.

**Depends on:** Step 8.

---

## Step 10 — Reporting / observability *(parallel, after Step 6)*

**Goal:** a human-readable feasibility report (region + bands + sensitivity ranking + Thor wall + A-vs-B gap) rendered from the results, plus the append-only `results/results.tsv` kept authoritative.
**Why now:** the numbers are only useful if reviewable; independent of the modeling core.

### Tests first
- [ ] `tests/test_report.py` — the report includes, for every feasibility claim, a confidence band and the calibration status; a report generated from a non-calibrated run is refused (consistency with P6).

### Implementation
- [ ] `fmrpu/report.py` — Markdown/HTML report generator. (Optionally hand off to the `system-design-visualizer` skill for a polished review artifact, since `docs/system-design.md` is source-grounded.)

### Acceptance
- [ ] `test_report.py` green; a sample report is produced from a golden run.

**Depends on:** Step 6.

---

## Definition of done (whole plan)

- [ ] Steps 0–9 complete; Step 10 complete or explicitly deferred.
- [ ] P1–P8 are green CI merge gates.
- [ ] The golden path (§A) reproduces a **real** measured B200 anchor within 15% on latency **and** energy (requires §D1 data). Until then, the pipeline runs on non-authoritative fixtures and **refuses** to emit FM-RPU feasibility.
- [ ] Simulator A emits the A8 deliverables (feasibility map, BW-vs-compute crossover, min-viable-spec frontier, Thor wall, B200-at-head-power ratio) as regions with bands.
- [ ] Simulator B emits the union provisioning point and the A-vs-B DreamZero gap, with the core proven unedited by B (P8b) and the Part-C tier-collapse condition reported.
- [ ] Every result carries: confidence bands (P7), calibration status (P6), and a `thermal_limited` flag (Step 5).

---

## §A — Golden-path integration test (the spine)

```
GIVEN  fixtures/anchors/b200_dreamzero_3step.json  (measured: latency, energy, config)
WHEN   the full Simulator-A pipeline runs with the calibrated utilization model
THEN   modeled latency and energy each match the measured values within 15%
AND    the full FeasibilityRegion result matches fixtures/golden/b200_dreamzero_3step.json
       byte-for-byte after float canonicalization
AND    the run is refused (CalibrationNotPassed) if the anchor is flagged non-authoritative
```

Runs after every step from Step 4 onward. If it goes red, the most recent step caused it.
The golden file is re-stamped **only** at the end of a step that intentionally changes the
modeled result (never mid-step).

## §B — The iteration loop

```
Read the failing assertion verbatim
  └─ Is the test's invariant correct?
       ├─ No  → fix the test + note why in the PR
       └─ Yes → fix the impl (minimum change OR rewrite the file fresh against the test)
Re-run the failing test → run the golden path → green ⇒ done
```

**Stuck > 30 min on the same failure:** stop; write expected-vs-observed in the PR draft;
print actual values (roofline intensities, byte breakdowns) then revert the print; re-read the
step's Acceptance block; **consider rewriting the stuck module from scratch** against its
acceptance test; if still stuck, escalate in the PR and do **not** start the next step.

## §C — Out of scope (Tier 1)

- Tiers T2–T4 (dataflow/Timeloop, cycle-approximate/SCALE-Sim+Ramulator, RTL/tapeout) — promoted per-point only after T1 survival (A7).
- The motor-control island's internals (modeled only as a 200 ms deadline consumer).
- Model *training* and task-success evaluation — the step/horizon-compression ceiling is an **input range** (swept / MC), not something this instrument measures.
- Pixel decode / reconstruction (dropped by the fork; only the decode *operator* is excluded, per P4).
- Any hardware-specific microarchitecture beyond the `HardwareRow` parameter set.

## §D — Design tensions surfaced for review

**D1. The calibration data is an external input the simulator cannot invent.**
No FM-RPU result is trustworthy until the measured anchors (§0.1–0.2) are supplied and
reproduced within tolerance.
- (a) Block all FM-RPU output on real, authoritative anchors — *honest, but nothing ships until data lands.*
- (b) Ship the pipeline against clearly-flagged synthetic anchors that **cannot** produce an authoritative feasibility claim — *unblocks development; the gate (P6) still refuses real conclusions.*
**Recommendation: (b) for the build, (a) for any result you circulate.** The plan wires P6 so the two can't be confused. **You must provide the B200 fork + Thor anchor data before Step 4 can pass authoritatively.**

**D2. Tier-1 fidelity ceiling vs the 15% tolerance.**
Analytical roofline omits scheduling, bank conflicts, and interconnect; the 15% that holds on
calibration may not hold when extrapolating to an un-built memory system.
- (a) Trust T1 feasibility as final — *cheap, risky.*
- (b) Treat T1 as a **screen**; promote only surviving frontier points to T2/T3; stamp the tier on every result.
**Recommendation: (b)** — matches A7; the plan already stamps tier and forbids single-point claims.

**D3. `N_new` (1.5–3.1k tokens/step) and realized BW utilization are the load-bearing unknowns.**
The conclusion hinges on these two (A6.4).
- Treat both as first-class swept/MC inputs with wide priors; report the sensitivity ranking prominently.
**Recommendation:** do not default them to point values anywhere; Step 6's sensitivity output must surface them.

**D4. Overfitting the utilization/`e_byte` fit to the B200 anchor.**
B200 (HBM3e) and FM-RPU (HBM) are different memory systems; a fit tuned to one may mis-extrapolate.
- **Recommendation:** hold out the Thor anchor for cross-validation (wired as `test_calibration_crossval.py` in Step 4); widen `e_byte` priors in MC rather than trusting a single fitted value.

**D5. Simulator-B union gate: hard-AND or soft?**
Does the union point require clearing **both** modes at 5 Hz @ 2 s simultaneously, or is a
per-mode near-miss acceptable?
- **Recommendation: hard-AND** (Step 8 `test_union_point.py` rejects a point that clears only one mode) — a general chip that misses either workload's deadline is not general.

**D6. The JEPA predictor is empirically 1–2B, not the 14B core (F3 — thesis-critical).**
Part C's "generality is nearly free" argument, and the B1 "same 14B DiT core" row, implicitly run
JEPA on the 14B backbone. Real JEPA world models are 1.2–2B ([V-JEPA 2 = 1.2B](https://ai.meta.com/blog/v-jepa-2-world-model-benchmarks/); DINO-WM smaller). On the *DreamZero* workload B still runs the 14B HBM path, so the headline likely survives — but the **cost of generality** (union over-provisioning + leakage) is set by the JEPA compute headroom `(JEPA_params × M × H)` and JEPA's own residency regime, both of which change at 1–2B.
- (a) Keep the 14B-JEPA assumption — *simple, but the leakage estimate is unverified and probably wrong.*
- (b) Make JEPA size a swept input; price the union point and A-vs-B gap at the real 1–2B point.
**Recommendation: (b)** — wired as `test_jepa_size_swept.py` (Step 8). Do not hardcode JEPA at 14B; let the simulator report the gap across the JEPA-size grid.

**D7. Identical-utilization (P1) is *fair* but not automatically *realistic* (F6).**
One utilization model for all rows prevents flattering the design-under-test — the honest T1
stance. But a specialized/systolic FM-RPU may genuinely achieve higher (or lower) utilization
than a GPU on the same operator, so identical-util can under- or over-state its real advantage.
- **Recommendation:** keep P1 as a **hard T1 invariant** (fairness first); treat per-architecture realized utilization as a **T2/T3 refinement** derived from Timeloop/SCALE-Sim, reported as a separate sensitivity — never leaking a per-row util fudge into T1.
