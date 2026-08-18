# Review audit — mechanical sweeps

Durable record of tree-wide sweeps for defect signatures that came out of
[`engineering-lessons.md`](engineering-lessons.md). A lesson that is checkable but
unchecked is half a lesson, so each sweep is recorded with its result.

---

## 2026-08-03 — Phase-3 boundary review

Three parallel adversarial reviewers (complexity, measured correctness, doc drift),
21 findings. Sweeps run after triage:

### S1. Unreachable code after a `__main__` guard  (lesson L7)

Signature: a test file defining classes or functions below `if __name__ == "__main__":`,
which `unittest.main()` makes unreachable because it calls `sys.exit()`.

Swept: every `*_test.py` and `test_*.py` under `sim/`, `bench/`, `tests/`.

| File | Result |
|---|---|
| `sim/systolic_test.py` | **DEFECT** — 4 SCALE-Sim reconciliation tests never ran. Fixed. |
| `sim/workload_test.py` | **DEFECT (recurrence, same day)** — 1 class never ran. Fixed. |
| `bench/contract_test.py` | clean |
| `tests/*.py` (pytest, 19 files) | clean; pytest collects by name, not by execution |

Now enforced mechanically in `scripts/check.sh`, because the written rule failed to
survive one hour.

### S2. `[M]` provenance tags on quantities a solver produced  (lesson L2)

Signature: the string `fitted` within one line of a `[M]` tag, plus manual inspection of
every `[M]` in the doc set.

| File | Result |
|---|---|
| `docs/WHITEPAPER.md:93-94` | **DEFECT** — two `[M]` tags on least-squares outputs. Retagged `[S]`. |
| `scripts/speedup_readout.py` | **DEFECT** — printed fitted constants with the word "measured". Fixed. |
| `public-website/chip.html` | **DEFECT** — same string on the public page. Fixed. |
| remaining `[M]` tags | inspected, all refer to real hardware runs |

### S3. Source directories outside the gate  (lesson L7)

| Directory | ruff | mypy | tests |
|---|---|---|---|
| `rpu/` | yes | yes | yes |
| `sim/` | yes | **added this sweep** | yes (Bazel, now called by `check.sh`) |
| `bench/` | yes | **added this sweep** | yes (Bazel, now called by `check.sh`) |
| `scripts/` | yes | no | no direct tests |

`scripts/` remains untyped and untested. Deferred: these are thin CLI wrappers over
tested library code, and `scripts/demo.py` is covered indirectly because its output
(`docs/SAMPLE_REPORT.md`) is diffed by the doc-drift reviewer. Revisit if a script grows
logic of its own.

### S4. Stale duplicated constants across repo and website  (lesson L3)

Signature: grep both repos for the pre-change value of every constant touched that day.

| Constant | Stale copies found | Result |
|---|---|---|
| anchor reproduction range | 7 (4 repo, 3 site) | all fixed |
| `1.17×` matmul cap | 3 (1 repo, 2 site) | all fixed; the number was also **wrong**, see L1 |
| operator FLOP split | 0 | already propagated |
| `compute_util`, `e_flop` | 0 in generated artifacts, 2 in prose | fixed |
| speedup curve literal | 1 (`feasibility.html`) | regenerated from live code |

Both generator-backed artifacts (`docs/SAMPLE_REPORT.md`, `chip.html`'s data blob) were
byte-identical to a fresh run. Every drift was in a hand-written number — the evidence
behind L3.

---

## 2026-08-04 — f_gpu measurement session

### S5. Wholesale-glob directories whose contents become program input  (lesson L11)

Signature: a `glob("*")` or `glob("*.json")` whose results are fed to a constructor without
a schema check, so an added file silently changes a computed result.

| Site | Result |
|---|---|
| `rpu/calibrate.py::load_anchors` (`fixtures/measured/`) | **DEFECT** — any JSON file joined the fit. Fixed: required-key check that names the file; regression test verified to fail without the guard. |
| `fixtures/anchors/` (same loader) | covered by the same fix |
| `sim/`, `bench/` data loads | none found; both take explicit paths |
| `scripts/design_space.py` | reads via `load_anchors`, inherits the fix |

### S6. Numbers relayed from a research agent without reproducing the arithmetic  (lessons L1, L10)

| Claim | Result |
|---|---|
| workload energy intensity `0.78 pJ/FLOP` | **DEFECT** — double-counted forward passes; implied 768 TFLOP/s against a measured 504 TFLOP/s ceiling. Corrected to 1.56-1.65 and re-derived from code. Had already been committed. |
| `f_gpu` bracket `6-25 %` | followed from the above; superseded by direct measurement |
| Eyeriss clock/ALU shares | verified against extracted text before use; correct |
| Leng guardband decomposition | source present in scratchpad; correct |

The corrected figure was caught by a physical sanity check, not by review: a workload cannot
be more energy-efficient per FLOP than a dense GEMM on the same silicon. **Prefer a sanity
check with a physical ceiling over another reading of the derivation** — the ceiling does not
share the derivation's mistake.

### S7. Bounds asserted with a guard in only one direction  (lesson L12)

Signature: a claimed floor or ceiling where only the too-good direction has a check.

| Claim | Guard present | Result |
|---|---|---|
| workload energy intensity | ceiling (cannot beat a dense GEMM) | caught the 2x error in minutes |
| arithmetic floor vs chunk budget | **none in the pessimistic direction** | **DEFECT** — a BF16 cost was used for an FP4 chip, understating the ceiling ~16x, and was committed as "arithmetic, not pessimism" |
| f_gpu ceiling from a GEMM | one-sided, and labelled as such in the module docstring | correct |
| eta from the bottom-up f-ratio | flagged "do not use as a predictor" | correct |

### S8. Numbers transferred across hardware regimes without a resemblance check  (lesson L13)

| Transfer | Regimes | Result |
|---|---|---|
| 94.7 %-of-GEMM -> Thor's expected efficiency | 19x above ridge, 600 W wall-powered -> 2x above ridge, 40 W | **DEFECT** — withdrawn; the regimes are not comparable |
| RTX-fitted `compute_util`, `e_flop_fp4_pj` -> Thor and RPU rows | workstation GPU -> edge SoC and un-built chip | **KNOWN AND UNRESOLVED** — already named in `PREDICTIONS.md` as the assumption most likely to be wrong; §3a-bis now records the mechanism |
| memory-bound result at 5 Hz -> the 40 W head-to-head | different binding constraint entirely | **DEFECT** — scoped in §7d after review |
| Thor peak spec -> Thor achieved efficiency | peak vs achieved | flagged in §7c, unresolved pending measurement |

**Method note.** Every defect in S7 and S8 was found by the reader challenging a claim, not by
a sweep. The sweeps above were written afterwards so the classes are checkable next time.

---

## 2026-08-05 — full-repo review (correctness, consistency, performance; TDD)

Inline review, no delegated reviewers (post-L10 choice). Merge gate stated up front:
`check.sh` + `bazel test //...` green, every defect leaves a regression test that failed on
the old code.

**Suite trust check first (L4).** Two mutation probes: breaking the CFG-reuse identity in
`rpu/workload.py` and the `pass_cycles` identity in `sim/systolic.py` each killed at least
one test. The suites can fail. Noted: the CFG mutation killed only ONE test, in an
obliquely-named file — coverage of that identity is thin.

| # | Finding | Class | Disposition |
|---|---|---|---|
| 1 | `chunk_energy` charged weights per step unconditionally while `chunk_latency` amortizes them under STREAM_PER_CHUNK — energy and latency described different traffic for the same draw. Latent: no current row's SRAM fits any model's weights, so all published numbers are BIT-UNCHANGED. | correctness (latent) | **Fixed**, red→green with `test_energy_and_latency_agree_on_weight_residency`; `simb.py` docstring updated to match |
| 2 | `required_efficiency_advantage` re-ran the full region — the eta-INDEPENDENT baseline included — at each of 40 fixed bisection iterations resolving to ~1e-11 against ~1e-3 MC noise. 13.2 s of a 45 s gate. | performance | **Fixed**: draws + baseline computed once, tolerance stop at 1e-4. Measured 12.6 s → 3.8 s (3.3x); `speedup_region` verified BIT-IDENTICAL against pre-refactor goldens; eta* within 2.7e-5. Call-count regression test added |
| 3 | The P1 grep guard matched `orin` inside "re-scoring"/"anchoring" — fired falsely on a docstring, and would have fired on any core comment containing "scoring". | tooling | **Fixed**: word boundaries; verified it still catches a planted real violation AND passes clean (both directions, L12) |
| 4 | "S = eta, exactly" (VC_CHEATSHEET/docs) is loose: eta divides only e_flop, so at parity S = 2.954 at eta = 3 (byte fraction 0.8% is correctly not divided — the DRAM interface is common). The bars are self-consistent because eta* is DEFINED through this code. | doc precision | Recorded here; wording is fine to keep since the machinery defines the number, but quote eta* from the code, never from the identity |
| 5 | `speedup_region` at THOR's native 130 W gives median S = 0.61 at eta = 2; x(130/40) = 1.98 confirms the TDP identity. The 2.05/2.15 bars therefore presuppose the parity (40 W) comparison — as documented. | consistency check | Verified, no change |
| 6 | Mutation coverage of the CFG-reuse identity is a single oblique test. | test gap | **Deferred** — tracking note added below; low risk while the identity is stable |

Modules read in full: energy, latency, speedup, roofline, montecarlo, thermal, opcost,
update_engine (head), simb (energy/latency paths), sweep (head+structure), sim/systolic
(prior sessions), sim/memory (prior sessions). Pattern sweeps: silent excepts (0), TODOs
(1, already flagged phase-4), mutable defaults (0), unit-literal drift (0).

**Verdict: production-ready for its stated Tier-1 scope.** The two real defects were latent
(1) and performance (2); nothing found that moves a published number — verified by golden
pins and a byte-identical regenerated `SAMPLE_REPORT.md`.

---

## 2026-08-05 — full-repo review (correctness, tests, performance; TDD)

Method: inline single-reviewer pass (no subagents, per the L10 incident), mutation probes
before trusting either suite, red test before every fix. Merge gate: `check.sh` + `bazel
test //...` green with all fixes in.

### Findings and triage — every finding in exactly one bucket

| # | Finding | Bucket | Disposition |
|---|---|---|---|
| 1 | `chunk_energy` charged weights per step unconditionally while `chunk_latency` amortizes them when SRAM-resident — same draw, two physics. Latent for every current row (7 GB vs 90 MB) | **Fixed** | Regression test red→green (`test_energy_units.py`); all current rows bit-identical; lesson L14 |
| 2 | `required_efficiency_advantage` re-ran the η-independent baseline MC at each of 40 fixed bisection iterations; interval resolved to ~1e-11 against ~1e-3 MC noise | **Fixed** | Draws + baseline hoisted, 1e-4 tolerance stop. 12.6 s → 3.8 s; `speedup_region` verified **bit-identical**; η* golden within 2.7e-5; call-count regression test |
| 3 | P1 fairness guard matched `orin` inside "re-scoring"/"anchoring" — no word boundaries; false-fired on a docstring | **Fixed** | `\b` added; verified it still fires on a real violation AND passes clean (both directions, L12) |
| 4 | "S = η, exactly" (docs) vs code: η divides only `e_flop`, so S = 2.954 at η = 3 — deviation equals the byte fraction (0.8 %) | **Reject (doc nit)** | Code is physically right (the DRAM interface is identical on both rows); η* is *defined* through this code so the bars are self-consistent. Not worth churning published text |
| 5 | Breaking the core CFG-reuse identity killed only ONE test, in an obliquely-named file | **Defer** | Note at `rpu/workload.py::forward_per_step`: the identity deserves a direct test naming F2 |
| 6 | `simb._residency_aware_energy_j` docstring described pre-fix `chunk_energy` | **Fixed** | Reworded: fetch count now shared; tier repricing remains B's job |

Modules read end-to-end: energy, latency, speedup, roofline, montecarlo, thermal, opcost,
update_engine; simb/jepa/sweep read at the load-bearing paths; report/calibrate reviewed in
prior passes this week. Pattern sweeps (silent excepts, mutable defaults, magic-string
branches, TODO debt): clean except one flagged phase-4 TODO in `sim/systolic.py`.

### S9. Sibling models re-deriving a shared physical rule  (lesson L14)

Signature: a physical decision (residency, regime, precision pricing) computed in one
module and independently hard-assumed in another.

| Site | Result |
|---|---|
| `rpu/energy.py` weight fetches vs `rpu/latency.py` | **DEFECT** — finding 1, fixed |
| `rpu/simb.py::_residency_aware_energy_j` | clean — imports the shared classifier |
| `rpu/jepa.py` latency + energy | clean — classifier for time; weights-once is the stated weight-stationary assumption |
| `sim/` vs `rpu/` traffic rules | intentionally separate tiers; reconciled via cross-checks, not shared code |

---

## 2026-08-05 (2) — full-repo review: code-vs-docs, test quality, complexity

Method: three parallel adversarial subagents split by axis (per the review-codify loop),
every finding re-verified by me against the source before any edit (L10). Two agents proved
findings by mutation; I replayed each mutation myself after fixing.

### Code defects (all verified by running the code)

| Defect | Evidence | Fix |
|---|---|---|
| `calibrate._util_from_vector` reset `static_fraction` to the class default | `fit(base=UtilizationModel(static_fraction=0.30)).util.static_fraction` returned 0.1 | `dataclasses.replace` so no future field can be dropped by omission; red test first |
| `memory.fusion_gain` computed `(total+scores)/total` = 56.71 while its docstring described `scores/total` = 55.71, and four doc sites published the docstring's number | ran it | docstring corrected to the code's (correct) quantity, `score_matrix_ratio` added, 55.7x -> 56.7x propagated |
| `CHIP_SPEC` quoted `ridge ~ 300` for the RPU | code gives 10,482; the same doc says ~10,500 fourteen lines earlier; 300 is the RTX's ridge | corrected |
| `hardware.py` carried a refuted `~250 TF` comment above the corrected 500 TF | both present in the file | corrected |
| `JepaParams` validated six fields, not `d` or `control_period_ms` | both load-bearing (L9) | validated |

Stale docstrings corrected: `report.py` and `calibrate.py` described a pre-measurement world
where the gate could not pass; `workload.py` said 87 % where the code gives 94 %; `simb.py`
quoted a 25x SRAM/HBM ratio true only of the defaults (80x fitted) and claimed both families'
residency used the weight working set (JEPA uses weights+act+KV).

### S11. Tests whose failure-detecting power was compromised  (lesson L15)

| Test | Defect | Proof | Fix verified by replaying the mutation |
|---|---|---|---|
| `test_thor_wall::test_wall_is_a_real_crossover` | asserted only "below the wall misses" | a mutant reporting the wall at a 0.998-miss bandwidth kept the suite green | both directions + "lowest clearing point" — mutation now fails it |
| `test_fairness::test_one_util_model_reaches_every_row` | compared a comprehension's keys to the set it was built from | a row-identity branch keyed on `hbm_bw` (naming no vendor, so `check.sh`'s grep guard missed it) passed the whole fairness suite | took THREE attempts, recorded in the test: a name-only twin sits on the same side of the threshold; epsilon-perturbation straddles no row's band; a fine sweep for step discontinuities works |
| weight-residency identity | tested only on hand values and `replace` overrides, never on `ALL_ROWS` as shipped | raising `RPU_14.sram_capacity` to 9e9 broke the central thesis with no test failing | asserted over `ALL_ROWS` — verified to fail on that edit |

### S12. Dead code and duplicated physical rules

Deleted after grepping each symbol: four `HardwareRow` fields with zero reads
(`hbm_capacity`, `dequant_tput`, `attn_engine_tput`, `interconnect_bw`), `ORIN_AGX_64`,
`jepa_chunk_energy_j`, `jepa_regime`, and `part_c_tier_collapse`'s ignored `base_util`
(the repo's only `_ = param`). ~180 lines.

The chunk power/energy formula was written out in **seven** places. Consolidated into
`rpu.energy.chunk_power`; `sweep` (x2) and `montecarlo` now delegate, pinned by a test that
reads their source and fails if either re-derives the static term.

### Not fixed, deliberately

- `sim/energy.py` (263 lines) has zero consumers. **Kept in the first pass** as a published
  negative result — its bottom-up ledger returns eta 29-55x, and `implausible_by` was the
  mechanical guard saying so. **Deleted on 2026-08-06** in the simplification pass: the
  negative result is recorded in four documents (`ETA_REPORT` 3b, `ROADMAP`, `PERF_LEVERS`,
  this file), so the module was carrying no information the docs did not already hold, and a
  wired-to-nothing module whose only output is a number we do not believe is a maintenance
  liability rather than an epistemic asset. `WorkReport.sram_bytes` and `per_op_cycles`, which
  existed only to feed it, went with it.
- `b200_at_head_power` (~65 lines, no callers, 35 W default against the 40 W parity rule)
  and most of `sweep.py`'s design-space surface are §A8 deliverables with tests as their
  acceptance gate. **Kept**, but the 35 W default is now a documented hazard.
- The `<1e-4` deadline-miss target is below the 20,000-sample estimator's 5e-5 resolution.
  Real, unfixed, and now recorded: the check is "<= 2 misses in 20,000 draws" and cannot
  distinguish 1e-4 from 6e-5.

### Method note against myself

My own mutation harness failed twice during this review: once leaving `roofline.py` mutated
so that six subsequent results were void, and once producing a false failure from stale
`__pycache__` after a byte-identical mutation. The concurrent code-vs-docs agent observed
both mutations in the working tree and correctly flagged them as suspicious. **Mutation
testing must restore under `trap`, verify restoration with `git diff`, and clear
`__pycache__` — same-size edits do not invalidate bytecode.**

### S13. Simplification pass (2026-08-06)

Bias toward simplicity, applied after the review's findings were verified. **582 lines
removed, 74 added.** Every deletion was grep-verified for callers first, and every script
that emits a published artifact was diffed before and after to prove the output is
byte-identical.

| Removed | Lines | Why it was safe |
|---|---|---|
| `sim/energy.py` + its test + BUILD targets | ~420 | Zero consumers; its negative result lives in four docs |
| `WorkReport.sram_bytes`, `per_op_cycles` | 8 | Existed only to feed the above |
| `b200_at_head_power`, `HeadPowerRatio`, `_scaled_to_power` | ~70 | Zero callers; superseded by `rpu/speedup.py`; its 35 W default contradicted the 40 W parity rule |
| `_RankedInput` | 8 | Built, sorted, immediately flattened to tuples |
| `_PJ_PER_J` / `_MS_PER_S` in four modules | 7 | Consolidated into `rpu/units.py` |
| `FM_RPU_UNION` x2, `_stage_labels` x2 in scripts | 24 | Consolidated into `scripts/_shared.py` |

**Two duplications that mattered more than their line count.** `scripts/design_space.py`
carried its own `TDP_W = 40.0` and `STATIC_FRACTION = 0.10` literals *and* re-implemented
the power cap that `rpu.speedup` owns — the identity the whole S = eta argument rests on,
duplicated into the script that emits the explorer grid. Now sourced from `RPU_14` and
`UtilizationModel`; output verified byte-identical. And `sim/workload_test.py` hand-wrote
`analytical_bytes = 45.9e9` because the hermetic suite cannot import `rpu`; that
reconciliation moved to `tests/test_model_seam.py`, where the figure is computed.

**Kept deliberately:** most of `sweep.py`'s design-space surface (the A8 deliverables, with
tests as their acceptance gate) and `bench.require_frozen` (forward-looking, and the gate
that makes the frozen-contract discipline real).

### S14. A superseded input surviving in a place the correction did not reach

Incident (2026-08-06): when 7e corrected the FP4 MAC energy (0.0125 was a double count),
the explorer's slider PINS were relabelled superseded and its PRESETS were not. The page
therefore showed a 0.73x downside corner computed from an arithmetic error we had already
published a correction for — a *fabricated pessimism*, which costs credibility exactly as
much as a fabricated optimism. Caught by the reader asking why the number looked so bad.
At the corrected pessimistic MAC energy the same corner is **1.60x**.

Signature swept: every place a corrected constant might still be embedded.

| Site | Result |
|---|---|
| explorer presets (`launch`, `mature`, `ceiling`) | clean — 0.006 / 0.006 / 0.0031, all inside the corrected range |
| explorer `downside` preset | **DEFECT** — fixed; test tightened from `< 2.05` to a `1.3 < eta < 2.05` band so a preset can no longer drift downward into refuted territory unnoticed |
| explorer pins | relabelled at correction time, correct |
| `docs/` prose | corrected at the same time as 7e |
| `archive/README.md` provenance | **STALE** — recorded commit 0d55070 while 24 commits had landed since. Updated to b188846 |

**Rule of thumb this reinforces (L15's cousin):** when a number is corrected, grep for the
OLD value across generators, presets, fixtures and provenance stamps — not just prose. A
correction that reaches the documentation but not the artifact leaves the artifact stating
the refuted claim to anyone who looks at it rather than reads about it.

### S15. The F1 landmine, stepped on despite the written rule (2026-08-06)

Incident: the explorer budget panel and ETA_REPORT 7b priced DRAM at "5 pJ/B [X,
LPDDR5X-class]" — 0.625 pJ/bit, below the best DRAM interface ever measured (WideIO 3D,
0.9 pJ/bit, VLSI 2013). A pJ/bit-class figure used as pJ/byte: exactly the 8x landmine
design F1 documents in rpu/units.py, and exactly why `pj_per_bit_to_pj_per_byte` exists.
The constant bypassed ingestion, so the converter could not protect it. Found by
cross-checking research-agent DRAM numbers (SpAtten 69% DRAM, T-REX 81% EMA) against our
"3-6% of budget" claim — the discrepancy was the alarm.

Blast radius: the calibrated model, bars and eta were NEVER affected (they use the fitted
e_byte = 64 pJ/B = 8 pJ/bit, which was right all along). Wrong were: the explorer budget
panel, 7b's two DRAM rows and its "memory is cheap in energy (3-6%)" claim, HANDOFF item
4, and session summaries. Corrected to 32-64 pJ/B -> DRAM is 18-37% of the chunk budget.

Fix beyond the number: a value guard now sits next to the constant — any DRAM pJ/byte
below 8 (i.e. under 1 pJ/bit) raises at build time with the F1 citation. The rule failed
as prose; it is now unrepresentable at the one site that bypassed the converter.

Sweep: grepped all pJ/B literals in scripts/ and docs/ for values under 8 used as DRAM
byte energy — no other instance.

---

## 2026-08-10 — external adversarial review of SIM_REVIEW_HANDOFF (20 findings)

The strongest external pass to date. Every finding triaged; none dropped. Verification of
the two number-moving claims done by us against primaries before acceptance (L10).

### Triage

| # | Finding | Bucket | Disposition |
|---|---|---|---|
| 1 | `f_ours` boundary ambiguous (numerator includes tree; denominator says "multipliers") | **ACCEPT P0** | Root cause of the implied-f pathology we had flagged. Interim: boundary caveat + guard downgrade (done). Full fix: ledger rebuild (below) |
| 2 | Compiler extraction as exact 1/c energy penalty assumes zero gating | **ACCEPT P0** | Correct: 1/c is the all-power-utilization-independent corner. The 2.04-vs-2.96 gap is less secure than stated; needs P(u) affine activity model. Until then the staging spread carries this caveat wherever quoted |
| 3 | S≈η 1.5% deviation vs DRAM 18-37% apparently inconsistent | **ACCEPT P0, diagnosed** | Both internally true but in DIFFERENT accountings: calibrated-GPU-anchored (byte fraction ~1%) vs first-principles-FP4 (DRAM 18-37%). Two accountings coexist across published artifacts; must be unified into one canonical equation with printed deviation |
| 4 | Anchors power-capped ⇒ E≈600·t ⇒ latency/energy not independent; 4 constraints vs 4 params | **ACCEPT P1** | Verified: all four anchors at 596.6-600.0 W. Fit quality ≠ validation. Split calibration/validation dirs; add Jacobian conditioning report |
| 5 | bw_util=1.0 refuted yet active in predictions | **ACCEPT P0 (policy)** | Footer now states the policy caveat; the fit/prior/prediction split is the real fix |
| 6 | Arithmetic energy needs a structured sub-term ledger | **ACCEPT P1** | Folds into the ledger rebuild; the 0.0031 "ceiling" value relabeled optimistic extrapolation |
| 7 | Implied-f guard uses incompatible boundaries; untrustworthy as rejection | **ACCEPT P0 — DONE** | Guards downgraded to boundary-caveated DIAGNOSTIC text in the explorer this commit |
| 8 | Thor 2070 TFLOPS is the SPARSE rating; workload contract forbids sparsity | **ACCEPT P0 — VERIFIED, OPEN** | Confirmed vs two secondary sources: dense FP4 = 1035 ⇒ dense peak 7.96 TFLOP/W. Our launch default (Thor achieved 9.0) EXCEEDS the dense peak — impossible on the contracted workload. Dense-peak pin added to the explorer. Headline recomputation deliberately HELD until NVIDIA primary confirms dense FP4 (sensitivity: launch ~2.0→~2.9-4.0, mature ~2.9→~4.3-5.9 — favourable, therefore held to the higher standard) |
| 9 | CFG KV sharing needs semantic proof (branch-dependent K/V cannot be shared) | **ACCEPT P0 audit — FOUNDER INPUT NEEDED [F]** | Code assumes context-KV is a once-encoded cache shared across branches (valid iff the fork encodes context once). If invalid, KV doubles to 15.5 GB/step and the 5 Hz bandwidth margin goes negative. Blocked on fork behaviour confirmation |
| 10 | 4.9× scheduled-vs-ideal traffic gap unexplained term-by-term | ACCEPT P1 | Cause-code ledger per byte above lower bound |
| 11 | Fleet NoC/clock/SRAM costs absent from geometry optimum | ACCEPT (= Phase 4.5, already roadmapped) | Geometry outputs relabeled "compute-array utilization optimum ignoring fleet interconnect" |
| 12 | Global overlap 0.9 hides the pipeline | ACCEPT P1 | Derive overlap from a small pipeline model; compare to 0.9 |
| 13 | Stage-cost fractions hard-coded in latency | ACCEPT P1 | Move to versioned workload spec |
| 14 | 20k MC cannot establish 1e-4 (95% UCB ≈ 1.5e-4 at zero misses) | **ACCEPT P0 (honesty) / P2 (estimator)** | Footer caveat added now; INSUFFICIENT-RESOLUTION verdict + rare-event estimator to follow |
| 15 | "Ceiling"/"downside" are scenarios, not bounds | **ACCEPT P0 — DONE** | Renamed launch/mature/optimistic/conservative design points across explorer + tests |
| 16 | Joint uncertainty absent | ACCEPT P2 | Probabilistic + bounded-robust modes |
| 17 | High-level factors can double-count; derive f from the ledger | ACCEPT (ledger) | The strongest argument for the rebuild |
| 18-19 | Static power as fixed TDP fraction; power/runtime fixed point | ACCEPT P2 | Physically explicit E(t) + feasibility solve |
| 20 | One canonical workload IR | ACCEPT (ledger) | With Sim-B independence preserved: B implements the spec, never imports A's counts |

**Rejected outright: nothing.** Partial pushback recorded on #2 (in a fully power-capped
regime a compiler derate that manifests as extra traffic/recompute IS an energy penalty;
the reviewer's point stands for the idle-bubble component) and #3 (each accounting is
internally consistent; the defect is their unreconciled coexistence).

### The two decisions deliberately NOT taken this pass

1. **Headline numbers not yet recomputed under dense-Thor semantics (#8)** despite the
   change being favourable — L12 discipline: a correction that raises our numbers gets a
   primary source (NVIDIA's own dense FP4 figure), not two secondary ones.
2. **The ledger rebuild (#1/#2/#3/#17/#20) not started inline** — it is a redesign of the
   simulator's core accounting and gets its own planned phase, not a same-day patch.

### 2026-08-10 (2) — review fixes #2/#3/#4/#5/#14 landed

All five implemented test-first (12 new tests in `tests/test_review_fixes.py`); the two
most load-bearing verified by mutation (a do-nothing prediction policy and a
certify-anything UCB both kill their tests).

- **#2** `rpu/extraction.py`: the 1/u compiler penalty is now the g = 1 corner of an
  explicit gating model. Consequence recorded: **the published launch figure is the FLOOR
  of a band** — 2.88 (no gating) to 4.19 (perfect gating) — to the extent the derate is
  utilization rather than energy overhead. Point estimate stays at the conservative end.
- **#3** `rpu/eta.py`: the canonical Amdahl-in-energy equation with a
  `SpeedupReconciliation` readout (eta-only vs full-ledger vs deviation), pinned on the
  reviewer's exact synthetic cases.
- **#4** `fixtures/validation/` with a `.validation` sentinel the loader REFUSES —
  fitting on held-out data is now mechanically impossible. And `identifiability()`:
  numerical Jacobian SVD at the fit point. **Measured result: singular values
  4.995 / 2.437 / 0.0207 / 0.000113, condition number 4.4e4 — the fit is effectively
  rank 2**, which is the reviewer's power-cap degeneracy argument made quantitative. The
  qualitative UNIDENTIFIED flag was, if anything, an understatement.
- **#5** `prediction_util()`: explicit fit/prediction split. The pinned bw_util = 1.0
  stays as the fit result; predictions get the measured 0.816 upper bound. e_byte keeps
  its fitted value with the policy reason stated (pinned at the conservative-direction
  bound, no independent measurement yet). Downstream consumers not yet switched — that
  flip moves golden artifacts and is a deliberate follow-up.
- **#14** `LatencyResult.miss_rate_ucb95` / `.resolves(target)`: rule-of-three at zero
  misses, normal approximation otherwise. 20,000 zero-miss draws now mechanically CANNOT
  certify 1e-4 (UCB 1.5e-4); 40,000 can.

Remaining from the review: the ledger rebuild (#1/#17/#20), overlap pipeline (#12), stage
spec (#13), traffic cause codes (#10), fleet pricing (#11 = Phase 4.5), joint uncertainty
(#16), static/fixed-point power (#18/#19), typed PeakThroughput (#8 infrastructure —
semantics corrected, type system pending).

---

## 2026-08-10 (3) — co-design investigation (model x SRAM x software brief)

New parallel instrument `rpu/codesign.py` + generated report
`docs/generated/CODESIGN_STUDY.md`. Production paths untouched (tested); no public claim
changed; all coefficients [T].

Findings: model size DOMINATES (the only knob reaching absolute 5 Hz in-ledger; full
weight residency is a real phase transition at <=1B models with ~1 GB SRAM, zeroing weight
DRAM traffic and external bandwidth). SRAM is a WEAK knob at the frozen 14B (<4% energy
swing across 32 MB-1 GB; 90 MB sits at the computed knee — now derived, was assumed).
Software: ADD BUT DERIVE — and the mechanistic ledger disagrees with the production 1/c
model by ~2.7x on the same baseline, the strongest quantitative argument yet for review
#2's rebuild. f_datapath derived from the ledger lands at ~24% at the baseline, inside
the assumed 15-25%.

Integrity: 9 tests, all named to the wrong implementation they reject; mutation-verified
on the residency threshold (size-only fit logic fails the capacity+lifetime test) and the
software rule (a blanket 1/u divisor fails the strictly-between test). Two of my own
defects caught during the build: idle energy initially mislabeled into the NoC category
(violating one-joule-one-category), and report prose asserting an under-provisioning
penalty the model did not yet implement — the penalty was implemented rather than the
prose kept.

### 2026-08-10 (4) — A/ledger consolidation

Hypothesis-first, per the brief: the A<->ledger 2.72x disagreement was decomposed EXACTLY
(closure tested to 1e-9) before any migration. **Result: overhead accounting 68%, software
32% — the software-dominance hypothesis is FALSIFIED** and recorded as such in a test
that fails if the balance flips silently. Consolidation proceeded on the corrected basis:
physics moved wholesale to rpu/ledger.py (parity vs pre-migration goldens tested to the
goldens' stored precision), codesign.py reduced to a physics-free client shim,
scaled_model homed in workload.py, reconcile.py kept as a permanent harness. Perfect-
gating anti-double-counting test added (halving utilization with g=0 must not double
energy); closure test mutation-verified (a broken factorization kills it). Cycle model
untouched; seam tests green. No public number changed; the published design points and
the ledger's ~7.8 both reproduce, now with their gap named instead of open.


## 2026-08-13 — third full review (post-consolidation code, adversarial agent + sweeps)

One adversarial review agent over the post-consolidation surface (ledger, reconcile,
design points, latency UCB, tests, docs) plus mechanical sweeps (artifact-regeneration
drift, physics-outside-rpu, zero-caller symbols). 10 agent findings, all verified against
source before action (L10); 2 sweep findings. Every finding triaged; none dropped.

### Triage

| # | Finding | Bucket | Action |
|---|---|---|---|
| 1 | CRITICAL: residency planner's KV footprint dropped the layer factor (2·n_ctx·d, not ·L); ~1.3 GB cache marked resident in 1 GB; study best point inflated 10.4→12.3x | fix | planner now imports `forward_per_step(p).kv_bytes` (L14); test pins the 1B/1 GB corner external; study regenerated |
| 2 | overlap-time formula under-charges at full overlap (below t_mem) and double-charges exposed time | fix | `overlapped_time_s` = max(compute, hidden) + exposed; unit-tested at both broken limits |
| 3 | miss-rate UCB normal approximation anti-conservative at k=1–5 (certified 2e-4 at k=1 where exact bound is 2.37e-4) | fix | exact Poisson-tail inversion for k>=1 (rule-of-three kept at k=0); tests at k=1, monotonicity, large-k agreement |
| 4 | closure test is an algebraic tautology (residual ≡ 1 by construction) | fix | L4 strengthened (recurrence); test now pins ratio/factor values with stated re-pin procedure |
| 5 | SOFTWARE_PRESETS transient registration leaks for any non-"ideal" name | fix | `evaluate` accepts `SoftwarePreset` instances; mutation pattern deleted everywhere; no-mutation test |
| 6 | Thor-achieved, launch accounting, 0.816 bound each typed twice | fix | single homes: `rpu/design_points.py` (new), `calibrate.BW_UTIL_MEASURED_UPPER` imported by ledger |
| 7 | test_explorer preset-band docstring still quoted pre-dense-Thor bands | fix | docstring matches assertions |
| 8 | SRAM-resident KV still charged 2x stream-through buffering | fix | resident KV reads SRAM once per use; exact-accounting test |
| 9 | package tier had infinite bandwidth (bytes in no time term), contradicting SIMULATORS.md | fix | `memory_time_s` with finite `PACKAGE_BW_BYTES_S` [T]; doc updated to match |
| 10 | SIMULATORS.md called 90 MB "the computed knee"; the sweep computes 96 MB | fix | doc says knee ~96 MB, adjacent to the chosen 90 |
| S | sweep: `eval_point` (the published-number identity) lived in scripts/, not rpu/ | fix | moved to `rpu/design_points.py`; explorer generator is a renderer |
| S | sweep: `prediction_util` / `eta_band_over_gating` have zero production callers | defer | deferral note at point of use; adoption re-pins goldens, waits for the Orin re-fit |

Consequences: ledger goldens regenerated (`fixtures/crosscheck/ledger_golden.json`, with
a `_provenance` key naming the physics change; the pre-migration file's parity purpose was
fulfilled and it is retired). The 14B baseline barely moved (power-cap-bound): ratio
2.7183, shares 67.7/32.3, ledger eta 7.82 — the documented 2.72/68/32/7.8 all survive as
rounded. The co-design study's Experiment 5 headline corrects 12.3x → 10.4x, and its KV
narrative is now computed from the sweep instead of asserted. No published design-point
number moved.

### S17. Re-derived quantity / twice-typed constant sweep (L14 recurrence signature)

Swept `rpu/` and `scripts/` for physical constants or derived quantities defined in more
than one module: found the four instances in findings #1/#6 (KV footprint, Thor achieved,
launch accounting, 0.816) — all fixed as above. Remaining known duplication is deliberate
and guarded: A vs the cycle model share no code by design (the seam tests are the guard),
and the explorer JS restates `eval_point` under a load-time golden check.

### 2026-08-13 (2) — chip-consolidation verification + architectural convergence

Prompted verification ("do we have a consolidated idea of the chip") swept every defining
parameter (peak, power, SRAM, memory system, array geometry, bar, terminology) across
CHIP_SPEC / CHIP_LAYOUT / system-design / ETA_REPORT / SIMULATORS / code. One real
S17-class recurrence found: **`rpu/hardware.py`'s Thor row still carried the sparse
2.07 PF rating three days after the dense-semantics decision** — the correction had been
applied to the explorer/design points but not to this sibling row, which feeds A's
latency/roofline stage times, the chipviz page, and the placeholder Thor anchor. Fixed to
1.035 PF dense; the self-declared placeholder anchor (`fixtures/anchors/thor_point.json`,
authoritative=false, values = the model's own output by design) and the golden-path file
regenerated with dated provenance; `test_required_eta` repaired (a 30 W clone of
dense-peak Thor shares the baseline's compute floor, so eta* = inf — correct behavior,
wrong synthetic premise; the DUT now carries the RPU-class peak). Website `chip.html`
payload regenerated in the same session (thor / stages / energy / eta_star sections).
Dated inline flags added at ETA_REPORT 7e's pre-correction sparse-identity layer and the
15.9 TFLOP/W table row; system-design row table now states dense.

Architectural convergence executed (user-directed): `rpu/codesign.py` shim retired
(clients import `rpu.ledger` / `rpu.workload` directly); SIMULATORS.md §8 records the
standing promotion plan — the ledger becomes the published accounting via ONE edit
(swap the design-point source, re-pin goldens, retire reconcile), gated on the Orin
measurement pricing the idle-gating factor. The headline switch is deliberately NOT
taken now: ledger coefficients are [T].

## 2026-08-17 (2) — CIM pivot evaluation (adversarial brief)

Full evaluation of the dual-mode digital SRAM-CIM transformer tile against B1 (the
existing digital RPU tile — NOT Thor), per the 34-section brief: same workload,
contract, node, external memory, 40 W. New instrument: `rpu/cim.py` (block-level
ledger, mutually exclusive categories, bundle-level [T] gain factors so peripheral
logic cannot hide, explicit weight/K-V write energies, capacity knee, memory-crossover
logic) + `scripts/cim_study.py` -> `docs/generated/CIM_STUDY.md` + 10 integrity tests
(no-free-lunch at unity parameters; Amdahl cap on linear-only; DRAM identical across
configs; ideal-CIM strands efficiency behind the memory roof; write monotonicity).

**Verdict: CONTINUE DIGITAL RPU, KEEP CIM AS GEN-2.** Central R_pivot = 1.48; the 2x
pivot threshold is reached only at (g_static>=3, g_dynamic>=3) — unsupported by
same-node evidence (the 9.43x literature anchor is vs a BF16/INT8 TPU baseline,
reproduced structurally by de-specializing our baseline) and already memory-bound at
the contract interface. Class ceiling R_E 4.53 but R_T only 1.95 at 40 W (2.3x
stranded). Writes and capacity are NOT the killers (good amortization at this
workload's reuse); the modest bundle gains vs an already-specialized FP4/FP8 path are.
The 7g prior (1.05-1.2x, rank last) directionally confirmed, slightly pessimistic;
superseded in place with a pointer. Re-open trigger: the phase-0 synthesized-tile
program pricing g_static at evidence grade.

### 2026-08-17 (3) — external no-context review of the public pages: one real fossil, one artifact

An outside reviewer (no simulator access) challenged the ceiling using the whitepaper's
energy split. Triage: (a) **REAL DEFECT** — whitepaper.html §5 still said "under 1% is
moving bytes": a fossil of the F1 pJ/bit-for-pJ/byte unit error (44.3 GB x the old
5 pJ/B = 0.6% of the launch accounting — arithmetic dates it exactly), contradicting
§9b's corrected 20-33%. The reviewer's inference chain (3D memory buys ~1.01x; delete
the 20-44x envelope) was VALID LOGIC FROM THE STALE PREMISE — S14 class: a superseded
input surviving where the correction did not reach. Fixed with a dated inline
correction crediting the reviewer; the split is now labeled an ARITHMETIC-energy
split with byte movement as its own system category. (b) **ARTIFACT** — the reviewer
"saw" the explorer's SELF-CHECK FAILED banner: the failure text was static HTML hidden
by CSS, so text-fetching readers see it as if fired. Verified the rendered page passes
(headless, payload match); template fixed so the message is injected only on actual
failure. (c) **CONVERGENT** — the reviewer's independent CIM Amdahl arithmetic
(1.36-1.98x hybrid) matches rpu/cim.py's grid within rounding, with no access to it.

### 2026-08-17 (4) — external close-read of the CIM study: one real defect, two adoptions

(a) **REAL DEFECT (prose contradicts own table, L4-adjacent):** the study's verdict and
grid-reading prose said "2x requires BOTH bundles >=3x" while its own grid shows
(5,2)=2.00 and (2,5)=2.20. Corrected in the generator with a dated note; strategic
consequence made explicit — a single-path breakthrough (especially ~5x dynamic-attention
CIM) remains a live pivot route and must not be prematurely killed. ETA_REPORT 7g row
fixed to match. (b) **ADOPTED:** the reviewer's periphery checklist (wordline/bitline,
peripherals, address/control, local clocks, write drivers, sense, accumulation trees,
I/O registers, inter-macro routing) is now the phase-0 measurement contract in the
study, with re-run decision thresholds; the study is explicitly labeled a SCREENING
study. (c) **CONVERGENT:** their reading of the mechanism (CIM wins by folding the
5.47 J reg/clock burden, not by cheaper arithmetic; bundles themselves rise 4.52->6.01 J)
is the study's own structural story, now stated with those numbers in answer 3; their
"CIM + much better edge memory" combination is the roofline-mover framing already in
7g-bis.

## 2026-08-17 (5) — radical world-model ASIC study (adversarial brief, layered on CIM)

New instrument: `rpu/radical.py` + `scripts/radical_study.py` -> RADICAL_STUDY.md, with
10 integrity tests (unity reproduces B1; area gate fires; hardening-alone loses;
phys-factor cannot scale static; memory roof strands speed). Headline structure: the
AREA GATE decides the question — logic-density hardening of 14B params needs ~12 reticle
dies (INFEASIBLE, and its leakage makes hardening-alone a net LOSS, R=0.97), while
ROM-recall hardening (2 dies) is feasible but caps g_hard ~2. Feasible frontier:
2.55x over B1 = ~7.4x Thor central [T]; ~9x optimistic-defensible; 10x only via
(g_A>=5 with optimistic hardening) or the gated low-voltage stack — rejected as a
roadmap claim per the brief's own standard. Ceiling C3 confirms 10x exists in the
budget. **Verdict: INCLUDE AS LONG-TERM STRETCH (~7–9x), no 10x claim; Gen-1 unchanged;
the phase-0 program gains a third macro (mask-programmed ROM weight bank) so one
synthesis run prices the CIM, radical-attention and hardening questions together.**
One near-miss caught pre-ship: the sweep-reading prose initially overstated the 10x
threshold geometry against its own table — the exact defect class of audit entry (4).

### 2026-08-17 (6) — FixedWeight (Taalas-style) study + Gen-3 roadmap incorporation

The FixedWeightTile brief evaluated through the existing radical instrument (the
shared-product mechanism — 16 products/activation amortized over fanout, ROM-selected —
is a hardening variant justifying g_hard~3 at ~16 transistors/param, 4 dies feasible).
**DECISION: INCLUDE as post-convergence Gen-3 tier; no published multiplier.** FW-alone
Amdahl-capped (1.3x); FW + best attention + 3D: central 2.8x/B1 = ~8x Thor anchored
(range 6.0–9.7) [T]. Overlaps quantified by recomputation: FW supersedes static CIM in
the lane (deletes weight memory besides the delivery bundle); 3D's absolute weight-side
saving disappears under hardening while the relative KV increment survives (x1.18 on
the leaner total) — tested. Anti-multiplication check explicit in the study. Gen-3 tier
written into CHIP_ROADMAP (trigger conditions, mechanism, kill criteria, three-macro
phase-0 pricing); ETA_REPORT 7g-bis and SIMULATORS updated. Full ladder re-verified
from instruments this session: 2.88/4.19/1.91/10.99 points, 1.91–15.7/22 range, expectations (median over defensible ranges) 4.4/6.4, CIM 1.48, radical frontier 7.4, FW 6.0–8.1–9.7, wall 35–47.

## 2026-08-18 — ladder finalization (structure, names, numbers, per-level statistics)

The ladder converged through user-driven iteration to its final form: four buildable
levels (first silicon / mature compiler / optimized / codesign) x (likely range 90% |
ceiling | what unlocks it), with the FP4 physics wall (~35-47x) as codesign's ceiling
and per-level corner bounds in the ceiling column (9.1; 15.7/22 north star; <=20-44).
Decisions recorded: north star dissolved as a row (resolution work, not unlock work —
its measurement bullets folded into first silicon, the sub-V_min tile into mature);
frontier/horizon renamed optimized/codesign; codesign numbered (~12x central, 7-19x
= optimized x 1.2-2x co-design residual [T], superseding the looser 15-25x estimate);
likely ranges replaced corner bounds as the headline statistic (same evidence, tighter
statistic; priors labeled: uniform + independence); likely_range() homed in
rpu/design_points.py with pinned tests (L1/L3); ceiling-name collisions resolved
site-wide (15.7 = bound/north star; "ceiling" reserved for the wall); deadline
guarantee removed from the table, retained as a Technical Roadmap section. All numbers
re-verified from instruments this date; archive parity confirmed; live pages verified
serving the final form.
