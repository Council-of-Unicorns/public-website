# Engineering lessons — etched

Rules distilled from real defects found in **this** repo. Every rule cites the incident
that motivated it, so it stays falsifiable: if the incident could not happen, the rule is
wrong and should be deleted rather than admired.

**Maintenance:** if an incident shows an existing rule failed to prevent a recurrence,
**strengthen that rule in place** and say why it failed. Do not add a near-duplicate.

Established 2026-08-03 at the Phase-3 boundary review (3 parallel adversarial reviewers,
21 findings).

---

## L1. A number nobody can reproduce is not a result, whatever tag it carries

**Incident (2026-08-03, review M4).** `docs/WHITEPAPER.md` claimed "matrix-multiply
specialization alone caps the speedup at 1.17×" tagged `[S]`, meaning our instrument
computed it. The instrument computes **1.59×**, and the analytic ceiling `1/0.621 = 1.61`
makes 1.17 unreachable under any reading. The number came from an external memo whose own
notes say it cites scripts that do not exist in this repo. It reached the whitepaper and
two public pages.

**Rule.** Before tagging a number `[S]`, run the code that produces it and paste the
output in the commit message. A figure imported from a document rather than from a run is
`[X]` at best, and if its source cannot be executed it does not go in a claim.

## L2. Fitted is not measured, and a passing gate does not mean identified

**Incident (2026-08-03, reviews C1-C3).** `compute_util` and `e_flop` are outputs of
`scipy.optimize.least_squares`, and were tagged `[M]` ("measured on hardware we ran") in
the whitepaper and printed with the literal word "measured" by `speedup_readout.py` and on
the public chip page. Worse, `e_byte_hbm_pj` and `bw_util` were resting on their box
bounds — determined by the bound, not the data — while the report said `Gate: PASSED`
with no qualification.

**Rule.** `[M]` means an instrument read a physical device. Anything a solver produced is
`[S]`, even when it was fitted to measurements. Any fitted coefficient resting on a bound
must be reported as UNIDENTIFIED wherever the result is rendered, not only in the roadmap.
`CalibrationReport.pinned_parameters` exists for this; if you add a fitted parameter, add
it to `_FIT_NAMES` so it is covered.

## L3. Hand-written numbers drift; generated numbers do not

**Incident (2026-08-03, review M1/M2/M3).** After a calibration change, commit `7a0d754`
stated "propagated to docs and site". Seven hand-written copies of the anchor-reproduction
range were not updated, and `feasibility.html`'s speedup curve was a stale literal that
plotted a visibly different curve from `chip.html` for the same quantity. Meanwhile both
**generator-backed** artifacts, `docs/SAMPLE_REPORT.md` and `chip.html`'s data blob, were
byte-identical to a fresh run. Every drift finding in that review was in a hand-written
number; not one was in a generated one.

**Rule.** A number that appears in more than one place must come from a generator. When
you change a constant, grep the whole tree *and the website repo* for its old value and
paste the grep result in the commit; "propagated" without that evidence is not a claim,
it is a hope.

## L4. A test that cannot fail is worse than no test

**Incident (2026-08-03, reviews M5/F1).** `test_shared_weight_stream_halves_dram_versus_naive`
asserted `naive/shared == 2.0`. The code scaled *every* byte by the same factor, so the
ratio was 6/3 regardless of whether the bytes were weights. The assertion held while the
underlying rule was wrong, hiding a ≥1.5× understatement of chunk DRAM traffic. The same
review found `test_dma_overlap_is_opt_in` asserting `total == compute` on a
compute-dominant shape, which blessed an overlap implementation that deleted the memory
term outright.

**Rule.** After writing a test, break the code deliberately and confirm the test fails.
For any test asserting a ratio or an equality between two paths, pick inputs where the
correct and incorrect implementations give *different* answers, and say in the docstring
which mutation the test is there to catch.

## L5. Cross-check against something that shares no assumptions with you

**Incident (2026-08-03, roadmap 3.3/3.5).** Three defects this session were found only by
comparing independent implementations: the cross-attention K/V token-count bug (found by
the `sim` model disagreeing 4.2% with `rpu`), the unphysical byte energy (found by
Accelergy's table, 16× lower), and the systolic drain semantics (found by SCALE-Sim). None
were findable by self-review: the brute-force reference in `systolic_test.py` shared the
model's own assumption about partial tiles, so it confirmed the wrong answer happily.

**Rule.** A model is not validated by a reference that shares its assumptions. Before
claiming a component is correct, reproduce it with an implementation written from
different premises, ideally somebody else's tool, and record the reconciliation including
what still disagrees.

## L6. Evidence that cannot discriminate between hypotheses is not evidence

**Incident (2026-08-03, review F3).** `docs/ROADMAP.md` claimed the SCALE-Sim
reconciliation was "RECONCILED EXACTLY" on four golden points. All four were measured on a
**square** 128×128 array, and on square arrays `S + R + C - 2` and `S + 2·max(R,C) - 2`
are identical. The rule the reconciliation claimed to establish was underdetermined by its
own evidence; the two forms diverge by up to 1.46× off-square. Three new points on a
32×128 array refuted the alternative and settled it.

**Rule.** When a measurement is meant to establish a formula, ask what *other* formula
fits the same points, and add a point that separates them. Symmetric test configurations
(square arrays, equal dimensions, powers of two) are the usual way this fails.

## L7. A split gate is a gate with a hole in it

**Incident (2026-08-03, reviews C1/M1).** The tree had two verification commands:
`scripts/check.sh` for `rpu/` and `bazel test //...` for `sim/` and `bench/`. Neither
ran the other. Four SCALE-Sim reconciliation tests sat unreachable behind a misplaced
`if __name__ == "__main__"` guard for a full session, and both halves reported green;
`mypy` covered `rpu` only and a real type error sat unnoticed in `sim/`. The roadmap
claimed those tests were "regression-tested".

**Recurrence (same day).** The identical defect reappeared in `sim/workload_test.py`
within the same session: a test class appended after the guard by the very edit that was
fixing the first instance. A written rule did not survive one hour. `scripts/check.sh` now
checks the signature mechanically, which is the only reason it was caught.

**Rule.** One command gates the whole tree. If a new source directory is added, it goes
into `scripts/check.sh`, into the mypy `files` list, and into the Bazel graph in the same
commit that creates it. When you claim a test enforces something, run the suite verbosely
once and confirm the test name appears in the output.

## L8. Report a bound as a range, never as a point

**Incident (2026-08-03, reviews M2/F6).** `sim`'s DRAM figure used a deliberately crude
two-state residency policy but returned a single float, and `simulate_chunk` reported it
alongside cycle counts as though both had the same standing. It sat ~50× above the
analytical model, and a one-element shape change swung it 8.5×.

**Rule.** If a quantity is computed under a policy known to be crude, return the bound
explicitly (`_min`/`_max`, or a range type) and say in the docstring what the endpoints
mean. A consumer that wants a point estimate must be forced to choose one knowingly.

## L9. Validate inputs at the boundary, or the model will answer questions about
impossible worlds

**Incident (2026-08-03, review F2).** `WorkloadParams` had no `__post_init__`.
`diffusion_steps=0` reported a FEASIBLE 44 ms chunk at 3 W; `diffusion_steps=-1` reported
−66.8 J and −1504 W. No exception anywhere. `montecarlo.py` clamped with `max(1, ...)`
while `sweep.py` passed the raw value straight through, so the guard was known to be
needed in one place and missing in another.

**Rule.** Every parameter dataclass validates its own invariants in `__post_init__`.
Fail loudly at construction; a defensive clamp at one call site is evidence the type is
missing a guard, not a fix.

## L10. A delegated finding is a claim, not evidence, until you have seen the source

**Incident (2026-08-04).** A research subagent investigating arithmetic energy returned a
detailed, well-formatted report with precise figures and paper citations: LNS measured at
190.3 fJ against INT8's 160.2 fJ at 7 nm, an L-Mul degradation chain, PERCIVAL posit
area and power, Qualcomm gate counts. It later retracted the entire report as fabricated.
Some of the cited papers exist; the numbers attributed to them were invented.

The failure did not stop there. **The findings were relayed to the founder, and worse,
multiplied by a legitimate calculation** (our own 73.3 % FP8 energy share) and presented
as a derived result of ~3x on arithmetic energy. Dressing invented inputs in real
arithmetic made them more credible, not less. The true domain total was ~1.05-1.16x.

A structural check would have caught it before it was relayed: the same report contained
a ceiling argument (multiplier is 11-17 % of MAC energy, math is ~47 % of accelerator
energy) that caps any multiply-side technique at ~1.07x. The headline 3x contradicted the
report's own ceiling by a factor of three, and nobody reconciled them.

**Rule.** Numbers from a delegated agent are **claims** carrying the agent's name, not
evidence. Before a delegated figure is relayed, committed, or computed with:
(a) it must cite a source you can open, and for anything load-bearing you open it;
(b) it must be reconciled against any ceiling or invariant stated in the same report,
because a result that contradicts its own bound is fabricated or misunderstood;
(c) if it survives, it is tagged `[X]` with the citation, never `[S]` or `[M]`.
A precise figure with no readable source is the signature to distrust, and precision is
what makes it persuasive.

## L11 — a globbed data directory is code; guard its schema at the boundary

**Incident (2026-08-04).** `scripts/measure_fu_fraction.py` wrote its cross-check artifact
to `fixtures/measured/rtx_pro_6000_fu_fraction.json`. `load_anchors` globs `*.json` from
that directory and turns every document into an `Anchor`, so the artifact was pulled into
the least-squares fit as a degenerate anchor and moved the fitted coefficients. No error
was raised at load time. The symptom surfaced as two *unrelated* calibration-gate tests
failing, which is an expensive way to discover that a data directory is executable input.

**Rule.** Any directory read by a wholesale glob is part of the program's interface, not a
scratch space. Validate the schema **at the loader boundary** and fail with a message that
names the offending file and says why it does not belong — never construct a partially
defaulted object from an unrecognized document. Artifacts that are deliberately *not*
inputs (cross-checks, derived reports, plots) live outside the globbed directory, and the
code that writes them says so at the output path. This is L9 (validate in `__post_init__`)
moved one level out: the same argument applies wherever untrusted shape meets a constructor.

**Related:** the cross-check that triggered this is itself an instance of L5 — it shares no
assumptions with the fit, which is exactly why it must stay out of the solver.

