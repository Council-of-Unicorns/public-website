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

- `sim/energy.py` (263 lines) has zero consumers. **Kept**: it is a published negative
  result — its bottom-up ledger returns eta 29-55x, and `implausible_by` is the mechanical
  guard that says so. Recorded as unwired rather than deleted.
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

