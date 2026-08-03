# ROADMAP — FM-RPU accelerator program

**Status: active. Supersedes `CHIP_ROADMAP.md`** (kept for the phase-1/2/3 chip-design
content it still owns; this document owns the simulation and validation program).

Adopted 2026-08-03 from the founder's systolic-array roadmap, reconciled against what
the repository already contains. The methodology is unchanged from that draft. Three
amendments and one reorganisation are recorded below, with reasons.

---

## The claim, and the standard of proof

> On the same model, inputs, quality threshold, batch size, latency boundary, and power
> envelope, Jetson Thor measures a specified latency and energy. The FM-RPU architecture
> projects a lower result, using a simulator cross-checked against independent analytical
> tools, validated against RTL, and calibrated with physical-design estimates.

Frozen in machine-readable form at [`bench/contract.toml`](../bench/contract.toml).
`bench/contract.py` refuses to mark that contract frozen while any blocking field is
unset, so an unmeasured baseline cannot pass itself off as a measured one.

---

## Three amendments to the adopted plan

**1. The baseline is Thor, not Orin.** Every published claim, the success criterion, the
whitepaper and the pitch target Jetson Thor-in-head. Orin is the previous generation, and
beating it in 2027 is a materially weaker claim that a customer evaluating head compute
would discount. Orin remains acceptable for *developing* the measurement methodology,
since it runs the same JetPack and TensorRT stack, but the published claim requires Thor
hardware before Phase 1 closes.

**2. The Stage-1 formula set must carry the energy-rate bound.** The adopted plan bounds
chunk time by compute and by memory. At head power neither binds. Chunk time obeys

```
t = max( t_compute, t_memory, t_comm, E_chunk / (TDP · (1 − f_static)) )
```

and in our measured numbers the fourth term exceeds the roofline terms by roughly an
order of magnitude. A simulator built without it optimises for the wrong wall and
concludes that a larger array helps, when it does nothing. This is the single most
load-bearing result the Phase-2 model produced, and every later phase inherits it.

**3. Physical-design credibility is a procurement dependency, not a task.** Phase 7 needs
PDK access, EDA licences, and foundry NDAs to produce numbers that mean anything at an
advanced node. OpenROAD with SkyWater or GF180 is free but lands at 130/180 nm, which
cannot support a 4-5 nm projection. Start the foundry or design-services conversation
during Phase 4, because the lead time exceeds the engineering time.

---

## Reorganisation: the existing repository is Phases 0-2

The adopted plan describes Stage 1 as an analytical model, simple enough to inspect by
hand, whose purpose is to reject impossible architectures and catch errors in the
detailed simulator. That model already exists and is calibrated:

| Plan phase | What already exists | State |
|---|---|---|
| Phase 0: define the claim | success metric, solid criterion, contract | claim defined; contract drafted, not frozen |
| Phase 1: measured baseline | 4 RTX PRO 6000 anchors within 0.5-3.9 % latency, 0.8-2.5 % energy; DVFS and FP8 sweeps | **wrong device** — proxy silicon, not Thor |
| Phase 2: analytical model | `fmrpu/`, ~2.5k lines: operator costs, roofline, energy, thermal, Monte Carlo, sensitivity | complete and calibrated |
| Sec 9: apples-to-apples | one shared utilization model across every hardware row, test-enforced | complete |
| Sec 10.5: sensitivity | Monte Carlo sensitivity ranking with confidence bands | complete |

Phases 3 and later are genuinely new. Nothing was deleted to make room.

### Known defects the new phases must fix

1. **`e_byte_hbm_pj` rests on its box bound.** CONTAINED 2026-08-03 (3.4): the bound is
   now physical (8 pJ/bit, against Accelergy's 1.56 pJ/bit table figure) and the fit
   reports the parameter as unidentified. Still not measured; a memory-bound anchor is
   what would identify it.
2. **`bw_util` rests on its bound (1.000).** Also now reported as unidentified. The
   model assumes 100 % of peak DRAM bandwidth, which no real controller achieves, and
   the compute-bound classification rests on it. Phase 4 replaces it with a modelled
   controller.
3. **No memory-bound anchor exists.** The founder measured WAN-class models as
   bandwidth-bound on B200; the instrument has never reproduced that regime.

Together these mean the Phase-2 model cannot currently settle any memory question. That
is the specific hole Phases 3 and 4 close.

---

## Phases

### Phase 3 — GEMM-level cycle model  *(in progress)*

Deliverable: a validated GEMM simulator, cross-checked against independent tools.

- [x] **3.1 Stage-2 systolic core.** `sim/systolic.py`: array geometry, three dataflows,
      wavefront fill and drain, partial tiles, edge underutilization, SRAM and DRAM
      traffic, DMA cycles with overlap as opt-in. Stdlib only, independent of `fmrpu/`.
- [x] **3.2 Hand-checkable validation.** `sim/systolic_test.py`: the closed-form cycle
      identity proven against a brute-force enumeration of every (cycle, row, col) MAC
      event, exhaustively over dimensions 1-16 and five array geometries, plus
      hand-computed corner cases.
- [x] **3.3 SCALE-Sim cross-check. RECONCILED EXACTLY.** SCALE-Sim 2.0.2, 128x128
      output-stationary. Our model reproduces its cycle counts on every shape tested,
      once two differences are accounted for, and both are now modelled rather than
      hand-waved:
      1. *Counting convention.* SCALE-Sim reports the index of the final cycle, so our
         count is exactly one higher per layer. Not a disagreement about hardware.
      2. *Partial-tile drain.* SCALE-Sim charges fill and drain across the whole
         physical fabric; our first version charged only the active sub-array, which
         is optimistic by (rows - active) + (cols - active) cycles per pass. Real
         hardware pays the full traversal without a bypass path, so
         ``drain_through_physical_array`` now defaults to True. Our DiT shapes are
         multiples of the array edge, so the two forms coincide on the real workload;
         the divergence would only bite on ragged shapes.
      SCALE-Sim 3.0.0 crashes in its memory model on both bandwidth modes
      (``TypeError: only 0-dimensional arrays can be converted to Python scalars``);
      2.0.2 is what we use. The measured values are pinned as golden data in
      ``sim/systolic_test.py`` so the agreement is regression-tested without the tool.
- [x] **3.4 Accelergy cross-check. DEFECT 1 CONFIRMED AND CONTAINED.** Accelergy's
      table plug-in gives 100 pJ per 64-bit LPDDR4 access, i.e. **1.56 pJ/bit**;
      published DRAM figures run roughly 1-8 pJ/bit. Our fitted ``e_byte_hbm_pj`` sat
      at 200 pJ/B = **25 pJ/bit, 16x above the table value**, because it was resting on
      its box bound. Two fixes landed:
      1. The ceiling is now 64 pJ/B (8 pJ/bit), generous for GDDR7 including PHY and
         controller. The fit still pins there, which is the conservative direction.
      2. **The fit now reports which parameters rest on a bound**
         (``CalibrationReport.pinned_parameters`` / ``.identified``). Compute-bound
         anchors carry no signal about byte energy or bandwidth utilization, so those
         two are reported as UNIDENTIFIED rather than quoted as calibrated. This is the
         systemic fix: the failure mode was silence, not the number.
      Consequences: e_flop_fp16 1.334 -> 1.426 pJ and compute_util 0.838 -> 0.805 as
      the fit rebalances. The speedup claim is unaffected, verified: at power parity
      S = eta exactly (eta 1.0 -> 1.000, 2.15 -> 2.131, 3.0 -> 2.954).
      Timeloop is NOT done: it needs a C++ build with libconfig/yaml-cpp/boost. Deferred
      to Phase 4, where its mapping and access counts matter more than they do here.
- [x] **3.5 Reconcile against Phase 2. EXACT.** Feeding the same operator shapes
      through both models initially disagreed by 4.2 % on total FLOPs, localised
      entirely to cross-attention, which was charging its K/V projection over the
      3120-token chunk instead of the 256-token text sequence, carrying 2 d^2 of
      projection weights where Q/K/V need 3, and omitting the attention-apply half.
      After the fix the two models agree to a ratio of **1.00000** with every operator
      split matching to 0.0 points. Since they share no code, that agreement is the
      evidence. Published splits were corrected in the docs and on the site.

**Gate:** cycle counts agree with SCALE-Sim within a stated tolerance, and any residual
difference has a named cause.

### Phase 4 — Memory and system scheduler

SRAM capacity and banking, bank conflicts, DMA engines, double buffering, external memory
timing via Ramulator, multiple arrays, event-driven dependency scheduling. Replaces the
two-state DRAM residency policy in `sim/systolic.py` with a real allocator, and replaces
`bw_util = 1.0` with a modelled controller.

**Gate:** defects 1 and 2 above are retired with measured or modelled values.

### Phase 5 — Full-model execution

Non-GEMM operators (RMSNorm, softmax, SiLU/GELU, RoPE, quantise/dequantise, reductions,
transposes, residuals), fusion, whole-graph scheduling, preprocessing, runtime overhead,
postprocessing. Attention carries ~62 % of dynamic energy, so the vector and reduction
path decides whether the GEMM advantage survives.

**Gate:** end-to-end projected latency and energy for the frozen contract, in both
accelerator-only and end-to-end boundaries.

### Phase 6 — RTL validation

Reduced array, banked scratchpad, DMA, command queue, basic vector unit. Same command
stream through the architectural simulator and Verilator; compare outputs, per-command
cycles, memory accesses, stalls, totals.

**Gate:** deterministic blocks agree essentially cycle for cycle.

### Phase 7 — Physical-design calibration

Synthesis and place-and-route of representative blocks. Achievable clock, array area,
SRAM access time, NoC delay, dynamic power, leakage, clock-tree power, fed back into the
simulator. Replaces every guessed constant. See amendment 3 for the procurement lead time.

**Gate:** the architecture retains its advantage under the pessimistic column of the
sensitivity table.

### Phase 8 — FPGA prototype

Compiler, command processor, drivers, runtime, long-running stability, deadlock freedom,
full-model numerical correctness. The FPGA proves the system works; it does not predict
ASIC speed, power or area, and no projection may cite it as if it did.

### Phase 9 — First silicon

Accelerator or chiplet only: arrays, vector and reduction units, SRAM, NoC, DMA, host
interface, external memory. Cameras, codecs, networking, CPU and OS stay on an existing
host. A complete robotics SoC is a later product, not this one.

---

## Sequencing note: the accelerator attaches to a host

The adopted plan makes the first product an accelerator behind PCIe or a coherent link
rather than a Jetson replacement. That is commercially right and it is what we will do.
It does interact with one existing claim: the deadline-miss-rate guarantee currently
rests on a zero-OS, statically scheduled datapath with no host in the loop. With a host
submitting commands, host jitter enters the end-to-end path. Phase 5 must therefore report
both the accelerator-only and the end-to-end boundary, and the miss-rate claim must be
restated against the boundary it actually holds for.

---

## Phase acceptance gate

Every phase closes with a `review-codify-loop` run: parallel adversarial reviews split by
axis, every finding triaged into fix / defer-with-note-at-point-of-use / reject-with-reason,
and the resulting rules committed to [`engineering-lessons.md`](engineering-lessons.md) in
the same change as the fixes. Phase 3 closed this way on 2026-08-03 with 21 findings.

## Working rules

- **Own the semantics, delegate the scaffolding.** Cycle equations, memory semantics,
  resource constraints, comparison methodology and validation criteria are owned by a
  human who can explain where every millisecond comes from. Graph import, sweep
  infrastructure, report generation, refactoring and test expansion may be delegated to
  agents with narrow, falsifiable tasks.
- **Two simulator modes.** Performance mode tracks shapes, dependencies, resources and
  traffic without computing tensor values. Functional mode executes small tensors against
  PyTorch to validate semantics. Performance mode answers how fast; functional mode
  answers whether it computes the right thing.
- **Never fake a measurement.** State what was run and the real result. If a gate failed
  or a step was skipped, say so. The contract validator enforces this for provenance;
  the rest is discipline.

## Build

Bazel 9 with bzlmod. `//sim` and `//bench` are stdlib-only, so the build graph is
hermetic and needs no package index. The numpy-dependent Phase-2 model in `fmrpu/` stays
on the venv and pytest path (`scripts/check.sh`) until its dependencies are vendored in.

```
bazel test //...        # sim + bench
bash scripts/check.sh   # fmrpu (ruff, mypy, pytest, grep guards)
```
