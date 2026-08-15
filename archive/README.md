# Archive — RPU program documents

Snapshot of the etched repo's documentation (source of truth:
https://github.com/Council-of-Unicorns/etched, `docs/`). Refreshed 2026-08-15 at etched
commit d5924ce+ (the frozen bar is S ≥ 2× at power parity — 2.05/2.15 are derived η*
requirements, retired from headline use 2026-08-10; dense-FP4 Thor semantics throughout,
design points 2.9× first silicon / 4.2× mature inside a bounded-robust 1.9–15.7×; the
2026-08-13 external review's ledger physics fixes and the two-instrument consolidation,
see SIMULATORS.md).

## Canonical documents

- [`WHITEPAPER.md`](WHITEPAPER.md) — the consolidated technical whitepaper (recruiting-grade;
  solid-beat feasibility, thermal co-design, roadmap).
- [`system-design.md`](system-design.md) — the simulator's architecture source of truth,
  including the §A8a success metric (solid-beat criterion).
- [`CHIP_SPEC.md`](CHIP_SPEC.md) — RPU v0.2 working spec (targets, latency bounds,
  memory architecture, operating modes, gates).
- [`CHIP_LAYOUT.md`](CHIP_LAYOUT.md) — floorplan, block budgets, dataflows.
- [`CHIP_ROADMAP.md`](CHIP_ROADMAP.md) — three phases, kill tests, gate criteria.
- [`PERF_LEVERS.md`](PERF_LEVERS.md) — workload optimization ledger after adversarial
  scrutiny (verdicts, per-mode multipliers).
- [`MEMORY_BANDWIDTH.md`](MEMORY_BANDWIDTH.md) — the memory wall taken seriously;
  demand/supply ladders under the no-aggressive-quantization constraint.
- [`SAMPLE_REPORT.md`](SAMPLE_REPORT.md) — example instrument readout (measured anchors).
- [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) — the completed simulator build plan.
