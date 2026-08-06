# ROADMAP — RPU accelerator program

**Status: active. Supersedes `CHIP_ROADMAP.md`** (kept for the phase-1/2/3 chip-design
content it still owns; this document owns the simulation and validation program).

Adopted 2026-08-03 from the founder's systolic-array roadmap, reconciled against what
the repository already contains. The methodology is unchanged from that draft. Three
amendments and one reorganisation are recorded below, with reasons.

---

## The claim, and the standard of proof

> On the same model, inputs, quality threshold, batch size, latency boundary, and power
> envelope, Jetson Thor measures a specified latency and energy. The RPU architecture
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
| Phase 1: measured baseline | 4 RTX PRO 6000 anchors within 0.5-3.9 % latency, 0.8-2.5 % energy; DVFS and FP8 sweeps | **wrong device and a synthetic workload** — proxy shapes on a workstation GPU, not a real checkpoint on a Jetson |
| Phase 2: analytical model | `rpu/`, ~2.5k lines: operator costs, roofline, energy, thermal, Monte Carlo, sensitivity | complete and calibrated |
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

### Phase 1 — measured ground truth  *(unblocked, not started)*

Runs in parallel with everything else and needs no simulator work. It is the only task
that converts our numbers from `[S]` to `[M]`.

- [ ] **1.1 Freeze the artifact.** Wan2.1-T2V-1.3B as the measurement vehicle: pin the
      repository revision, checkpoint and weights hash, and set the quality metric,
      threshold and dataset. Fills 8 of the 14 blocking fields in
      [`bench/contract.toml`](../bench/contract.toml).
- [ ] **1.2 Orin benchmark.** The hardware is in hand. **A sealed prediction is already
      registered** in [`PREDICTIONS.md`](PREDICTIONS.md): 59.1 ms and 2.68 J for one
      forward pass of the 1.3B vehicle. Do not tune the model before measuring, or the
      prediction is void and the measurement degrades from a test back into a fit. Optimized TensorRT, fixed power
      mode, thermal steady state, external power measurement; report p50/p90/p99, miss
      rate, energy per inference and per-operator timing.
- [ ] **1.3 Memory-bound anchor.**  ← **moved here from Phase 4 on 2026-08-03**
      A bandwidth-bound benchmark on the RTX PRO 6000. This is what identifies `bw_util`,
      which currently rests on its box bound at 1.000 and which no amount of simulator
      work can determine. It is also the anchor the founder's B200 WAN observation has
      been waiting for.
- [ ] **1.3b Module power decomposition.** NVIDIA publishes no per-block power for
      NVENC/NVDEC, ISP or the vision cluster, so it must be measured. `tegrastats` exposes
      three pre-regulator rails via two INA3221 monitors: `VDD_GPU_SOC` (GPU *and* SoC
      logic, where the codecs live), `VDD_CPU_CV` (Arm cores plus PVA/DLA) and
      `VIN_SYS_5V0`. The rails do not isolate the codec, so use delta measurement, the
      same technique as the DVFS idle audit: (a) idle with clocks up, (b) camera plus
      H.265 encode without inference, (c) inference without codec. That yields the codec
      cost AND the share of the module budget that never reaches inference, which is the
      quantity our module-level comparison turns on.
- [ ] **1.4 Export the operator graph** with exact shapes and traffic, so both sides run
      the identical workload.

**Gate:** the contract reaches `frozen`, `bw_util` is identified, and the system boundary
is written down — what is inside the 40 W on each side. Our accelerator needs a host and
provides no codec; Thor carries CPU, ISP, codecs and vision accelerators that leak into
the same budget. Undecided boundaries get resolved in whichever direction flatters the
person writing the slide, so this is decided before any measurement is taken.

### Phase 3 — GEMM-level cycle model  *(complete 2026-08-03)*

Deliverable: a validated GEMM simulator, cross-checked against independent tools.

- [x] **3.1 Stage-2 systolic core.** `sim/systolic.py`: array geometry, three dataflows,
      wavefront fill and drain, partial tiles, edge underutilization, SRAM and DRAM
      traffic, DMA cycles with overlap as opt-in. Stdlib only, independent of `rpu/`.
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

### Phase 4 — Memory and system scheduler  *(in progress)*

Ordered by what each step unblocks, not by what is interesting.

- [x] **4.1 Tile scheduler and capacity-aware allocator. DONE.** Replace the two-state
      residency policy with an explicit blocked-GEMM model: tile shape, loop order,
      SRAM working set, and per-operand DRAM traffic with real reuse. Search the tiling
      space for the minimum-traffic schedule that fits capacity. This is the step that
      makes any memory number meaningful: today `sim` reports 1.4-2.3 TB per chunk where
      the fused analytical model reports 46 GB. `sim/memory.py` does the standard
      blocked-GEMM analysis and searches the tiling space for minimum traffic subject to
      capacity. Result on real DiT shapes: projections improve 9-15x.
- [x] **4.2 Fused attention. DONE.** (Activation residency across operators is still
      open.) An intermediate that fits on chip never reaches DRAM. `sim` has no such concept, which is most of the remaining gap, and
      "fusion by construction" is a CHIP_SPEC claim that nothing checked. Now measured:
      the unfused score matrix is 233 MB per head per layer, and fusing it away is worth
      **56.7x** on attention traffic. Combined with 4.1, chunk traffic falls from 4.6 TB
      to 226 GB, closing the gap to the analytical model from **101x to 4.9x**.
- [~] **4.3 Energy ledger, and the first bottom-up η. BUILT, NOT YET USABLE.**  ← **the critical path**
      Component energies (MAC, SRAM read and write, DRAM access, control) times the
      activity counts the model already produces, giving mJ per chunk per component and
      therefore η. Structured as our own Hameed Table 3, cross-checked against Accelergy.

      This was **missing from the plan until the 2026-08-03 re-assessment**, and its
      absence was the plan's most serious defect: phases 3, 4 and 5 as originally written
      could all complete without ever producing η, which every claim the company makes
      depends on. They sharpen predictions of *time and traffic*; η stayed an input.

      It is also the cheap kill test the chip roadmap already specified: mapped η below
      2.2, or functional units below 35 % of energy, and the project stops before tapeout
      money.

      **Status: REMOVED 2026-08-06 after the finding below was recorded. `sim/energy.py` ran, and its first answer was a defect
      report.** Against the calibrated GPU baseline on the 14B chunk it returns
      η = 29-55x, an order of magnitude above TPUv4's published 1.6-3.2x ceiling. That
      is not a discovery; it means the ledger counts a bare multiplier against a whole
      measured system. It omits clock distribution, intra-array wire and interconnect,
      accumulator registers, the memory PHY, and leakage — which is most of a real
      chip's energy, and is exactly Hameed's point. `implausible_by()` makes the judgment
      mechanical, and a test pins the incompleteness so it cannot be forgotten; that test
      flips to failing the moment the missing components land.

      **Remaining work before η can be quoted:** add the five omitted components, then
      re-derive. Until then η stays an assumed input and no claim may cite this module.
- [ ] **4.4 Ramulator cross-check.** A modelled LPDDR5X controller for OUR chip: queues,
      banks, command scheduling, refresh. Note the correction below — this gives our
      controller's realized efficiency, and cannot identify the GPU's.
- [ ] **defer 4.5 Banked SRAM, bank conflicts, DMA engines** and **4.6 event-driven
      multi-array scheduling** until the energy ledger says cycles matter. Chunk time is
      `max(compute, memory, comm, E/P)` and the fourth term dominates by roughly an order
      of magnitude, so refining cycle counts sharpens a term that is ~10x from binding.
      Revisit if 4.3 changes that ordering.

**Gate (corrected 2026-08-03):** a bottom-up η with a stated uncertainty band, and `sim`'s
chunk traffic reconciled against `rpu`'s with any residual explained.

The previous gate said `e_byte_hbm_pj` and `bw_util` "are no longer reported as
unidentified", which **no work listed under this phase could deliver**. `bw_util` is a
coefficient of the *GPU calibration fit*; Ramulator models our own controller and says
nothing about NVIDIA's realized bandwidth. What identifies it is a memory-bound anchor —
a measured GPU run in the bandwidth-bound regime — which is a measurement task and now
sits in Phase 1 where it belongs.

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

## Finding: the architecture design space is flat, and that is a model artifact

`scripts/design_space.py` sweeps 84 points over array geometry (64/128/256 edge, MAC
count held constant), SRAM capacity (8-256 MB) and DRAM bandwidth (150-1200 GB/s), and
reports which wall binds at each.

**Every point is energy-bound, and forward-pass time is identical to within 2 %.**
Compute varies 1.8x across the grid and memory varies 9.5x; energy sits 9.3x above the
best compute time everywhere, so neither matters.

The tempting reading is "geometry does not matter, stop optimising it". The correct
reading is the opposite: **our energy model contains no term that depends on array
geometry, SRAM capacity or bandwidth**, so it is flat across those axes by construction.
Real silicon is not: more SRAM means more leakage and area, more bandwidth means more PHY
power, a different array shape means different wire energy. Those are exactly the five
components the Phase-4.3 ledger omits (clock, wire, registers, PHY, leakage) and exactly
why its bottom-up eta came out implausible. Same missing physics, two symptoms.

**Consequence for tooling:** an interactive design-space explorer over these axes would
render a flat surface with high production values. It becomes worth building when the
energy model depends on the parameters being swept, which is Phase 7. Recorded here so
the idea is not re-proposed before then.

## Stopping rule for simulator work  *(added 2026-08-03)*

Phases 6-9 need people, EDA licences and money that simulation does not, and simulator
fidelity can absorb unlimited effort. Once 4.3 produces η with an uncertainty band,
**any further simulator work must name the decision it changes.** Refining a number that
cannot move a gate is not progress, however satisfying the number becomes.

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
hermetic and needs no package index. The numpy-dependent Phase-2 model in `rpu/` stays
on the venv and pytest path (`scripts/check.sh`) until its dependencies are vendored in.

```
bazel test //...        # sim + bench
bash scripts/check.sh   # rpu (ruff, mypy, pytest, grep guards)
```
