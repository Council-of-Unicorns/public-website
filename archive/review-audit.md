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
| `fmrpu/` | yes | yes | yes |
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
