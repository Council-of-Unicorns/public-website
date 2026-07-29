# CHIP_ROADMAP.md — FM-RPU silicon phases

Refined roadmap (2026-07). Success bar: **S ≥ 2× Jetson Thor inference speed** on the
world-model workload, measured per `docs/system-design.md` §A8a (Thor-in-the-head basis,
~40 W neck ceiling). The calibrated Tier-1 instrument says the bar reduces to an
**energy-efficiency advantage η\* ≈ 3.1×** over measured Blackwell silicon at ≥ ~4 PF dense
FP4 / 40 W, power parity with Thor-in-head (power-limited regime — raw peak beyond that is irrelevant).

Gain decomposition (Tier-1 + literature judgment; Tier-2 must confirm per phase):
generic transformer etch ~70–75% of the log-gain, world-model datapath ~20–25%,
schedule etch ~5% of speed but 100% of the deadline-miss-rate guarantee and roughly half
the memory-interface power provisioning.

---

## Phase 1 — Etch the generic transformer (η target ≈ 2.2–2.4×)

The Sohu mechanism — remove the instruction stream, scheduling, and register-file churn;
spend the die on a fixed transformer dataflow — but at the **inverted operating point**.
Every knob below differs from a datacenter throughput part *because* the budget is joules
at a deadline, not tokens per dollar:

1. **Wide-and-slow V/f point — status: MEASURED ADVERSE (2026-07-15), reopened as a
   GATED side bet (2026-07).** The DVFS sweep shows η_vf = 1.00× within the GPU's
   operating envelope (energy/FLOP flat 1.0–3.09 GHz; voltage-floor-limited) — the lever
   is unavailable without sub-Vmin custom design. Phase-1's η target is therefore carried
   by items 2–5 (architecture; evidence TPUv4-class 1.6–3.2×). HOWEVER: Etched now claims
   sub-half-voltage math blocks in working A0 silicon ("Low-Voltage Inference"), and the
   near-threshold literature supplies a measured technique menu (split Vdd domains, 8T
   SRAM + assist, Razor-class adaptive margin ≈47% energy recovery, splittable arrays) —
   see CHIP_SPEC §6b. Disposition: **phase-1b test-structure tile on the gate-4 shuttle;
   never counted in the η bars (2.05 bare / 2.15 solid); pure upside if proven.** Data: fixtures/dvfs_sweep.json.
2. **Stretch-to-deadline static timing.** The 200 ms control period is a resource: size
   the pipeline so one chunk completes just inside it (~170 ms) at minimum viable
   voltage. Race-to-idle wastes V². Only legal because the schedule is etched (Phase 3
   formalizes the guarantee; the V/f sizing decision lands here).
3. **Parallelism from tokens × layers, not batch.** Arrays tiled to the model's static
   shapes (d = 5120, ffn = 13824, heads = 40; 3,120-token chunks), layer-pipelined.
   Utilization from shape-certainty, not occupancy machinery. Batch fabric: none.
4. **Memory as a conveyor, not a cache.** The chip streams the identical ~44 GB
   weight+KV sequence every chunk: exact prefetch, open-page sequential bursts, no
   caching/coherence logic, interface clocked wide-and-slow. Memory is 4–13 W of the
   40 W budget (instrument-computed) — conveyor discipline holds it to the low end.
5. **Sensor-to-action on one die.** No PCIe host loop, no serdes fabric, no
   multi-tenancy. Camera latents in, action tokens out.

**Gate (before Phase 2):** Tier-2 energy model (Accelergy/Timeloop-class, per §A7) of the
phase-1 datapath. Pass requires ALL of:
- **η ≥ 2.2** computed at the (array, conveyor) point, and **FU-energy fraction ≥ 35%**
  (the Hameed ISCA'10 diagnostic — CHIP_SPEC §6a);
- the **dataflow A/B decided**: Timeloop comparison of weight- vs output-stationary vs
  broadcast-tree on our exact shapes, including the per-pass (GEMM vs attention) split
  (CHIP_LAYOUT §6) — days of work inside the same toolchain, closes the last major
  microarchitecture unknown;
- the deliverable is a **staged energy ledger in the Hameed Table-3 format** (per-component
  mJ/chunk: IF-equivalent, SRAM, network, control, FU) so the gate review is a like-for-like
  comparison against the canonical published datapoint;
- Tier-1 speedup readout at the computed η shows **S p50 ≥ 1.6** vs Thor-in-head;
- a **real memory-bound B200/WAN anchor is ingested** (founder's profiling), `bw_util`
  identified, the compute/bandwidth crossover re-located, and the MACs-vs-channels
  provisioning ratio decided against it (MEMORY_BANDWIDTH.md §4).
(The FP8 anchor capture that previously gated this step is DONE — s measured 2.6–3.4.)

## Phase 2 — World-model datapath (η target ≈ 2.9–3.3× cumulative)

Hardwired FP4-dequant → FP8-attention mixed-precision path; attention engine shaped for
the fixed geometry (3,120 Q × 18,720 KV); fused per-layer pipeline for the exact operator
sequence (QKV → self-attn → out → cross-attn → FFN). Each is a shave on the same
FLOP-energy term the phase-1 etch attacks.

**Gate (solid-beat at power parity, revised 2026-07-29):** Tier-2 confirms cumulative
η ≥ 2.2 (which now coincides with the Hameed-derived kill floor) and the Tier-1 readout
shows **S p05 ≥ 2 in every mode** vs Thor-in-head (the solid criterion, §A8a). The
stacked-lever plan toward the η = 3 design target (utilization edge, Ledger-B
realization, sub-Vmin) must name its expected contributions. Below η 2.2, the phase-2
shaves missed and the design point is re-swept before more silicon effort.

## Phase 3 — Schedule etch + safety (the deployability phase)

CFG weight+KV pair-sharing guaranteed in hardware (halves HBM traffic → 2–7 W of
provisioning); rolling-KV shift-register window management; inter-step latents pinned
on-die; deterministic pipeline timing end-to-end. Adds ~5% speed; delivers the
deadline-miss-rate < 10⁻⁴ guarantee and the memory-power budget. The Part-B programmable
update engine (flow-ODE / CEM microcode, ~2% datapath cost) lands here — the generality
hedge is priced, not free-ridden.

**Gate:** Tier-3 (cycle-approximate + DRAM sim) shows the miss-rate target holds under
scheduling/bank-conflict effects; thermal model confirms sustained power within the neck
ceiling with margin.

---

## Ledger B — workload co-design levers (parallel; see PERF_LEVERS.md)

Quantified, scrutinized stack of workload-shaping levers (v2: ≈1.7–3.8× Quality /
1.4–2.6× Deadline [X/T]): the path toward the absolute-5 Hz goal that silicon alone cannot
reach (η≈12 at 40 W parity). Honest status: 5 Hz needs η≈3 + mid-stack, or a certified cross-chunk reuse
floor (the train-time co-design experiment). Verification pre-silicon: Tier-1 sweeps +
quality checks on the local RTX proxy. µcode/sequencer budget lands in gate 1.

## Standing instrument work (parallel)

- Real B200-class anchor (rented, few hours) to complement the local RTX anchor —
  cross-validates the fit across memory systems (D4).
- FP8/FP4 capture config in `scripts/capture_local_anchor.py` to collapse the `s` prior.
- Tier-2 harness bring-up (SCALE-Sim v3 + Accelergy + Ramulator, §A7) — needed by every
  phase gate above.

Every phase gate is a **kill test**: a phase that misses its η contribution sends the
design back to the sweep, not onward to more expensive fidelity. (§A7 discipline: promote
only survivors.)
