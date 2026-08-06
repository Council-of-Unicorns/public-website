# The η Report — the energy case for the RPU, and the design it forces

**Status:** synthesis, 2026-08-04. Supersedes no document; consolidates the argument that is
otherwise spread across [`CHIP_SPEC.md`](CHIP_SPEC.md) §6, [`PERF_LEVERS.md`](PERF_LEVERS.md)
Ledgers A–D6, [`MEMORY_BANDWIDTH.md`](MEMORY_BANDWIDTH.md) and the measured fixtures.

**Provenance tags, used on every load-bearing number.** `[M]` measured by us on hardware ·
`[S]` produced by our calibrated simulator · `[F]` founder-measured in production ·
`[X]` external literature, primary source opened · `[X*]` external, relayed by a research
agent, primary **not** opened · `[T]` target or estimate, not achieved.

---

## Summary

**We expect about 2.6–3.0× over Jetson Thor at equal head power, with a defensible range of
2.0–4.0× and a ceiling near 7×.** The bar is 2.15× and the design target is 3.0×.

**The baseline is Jetson Thor at 40 W head power, always.** Every multiplier in this
document is η against Thor. The RTX PRO 6000 appears only as the **calibration anchor** — the
silicon we can physically measure — and never as the thing we claim to beat; §3a-bis records
why it would flatter us if used that way. Any ratio in this report that is not against Thor
is labelled as such at the point of use.

**Two independent derivations converge there.** §7 anchors on TPUv4's published 1.6–3.2×
against a same-node A100; §7e derives the same band from Thor's spec sheet and the cost of a
multiply, using none of §7's inputs. That is the cross-check lesson L5 asks for.

| Term | Value | Evidence class | Counted in the bars? |
|---|---|---|---|
| η, architecture | **2.0–4.0×**, central 2.6–3.0 | `[T]`, bounded by `[M]` and `[X]` | Yes — this *is* the bet |
| Physical design | 1.2× (1.15–1.4) at system level | `[X*]` sized, `[M]` explained | No — gated upside |
| Ceiling, f_ours at Hameed's 35% | 3.5–7× | `[T]` | Requires beating every published DNN ASIC |
| Downside, defensible pessimism | **1.6×** | `[T]` | f_ours 15 %, Thor at 72 % of peak, v1 compiler. Below the bare bar |
| Compiler-maturity derate | **0.6–0.8× at launch** | `[T]` | §7f — gives **1.7–2.1× at first silicon**, 2.6–3.0× mature |

**The hinge is one number: the energy of an FP4 multiply-accumulate at the target node.**
§7e shows it fixes our floor *and* Thor's overhead fraction simultaneously, because Thor's
0.0628 pJ/FLOP peak is published. **The accounting was redone 2026-08-05** (§7e): the old
worst case — CHIP_SPEC §6's 0.0125–0.0178, which would have put Thor at 20–28% FU fraction
and ended the project — was a double count (a scaled MAC relabelled as a multiply, plus an
accumulator again). Corrected E2M1-with-adder-tree arithmetic is **0.0038–0.0057 pJ/FLOP**,
implying Thor at 6–9% and eta 2.2–3.3× at f_ours = 20% — reinforcing the central estimate
from a route that previously threatened it.

Three findings from this program constrain everything above, and all three are measured on
real silicon by us:

1. **DVFS buys nothing.** Energy per FLOP is flat from 1.0 to 3.1 GHz on the baseline `[M]`.
   The wide-and-slow story requires sub-Vmin custom silicon, not an operating point.
2. **The baseline is itself energy-bound — and under the cap, throughput ∝ efficiency.**
   Board power pinned at exactly 600.0 W in every arithmetic configuration we ran, and FP8
   delivered **1.76× the BF16 throughput at identical watts** — because it is 1.77× more
   energy-efficient per FLOP `[M]`. That is the project's S = η thesis measured on the
   baseline's own silicon. (An earlier 1.24× figure was a harness artifact; see §3c.)
3. **The GPU is not running our workload badly.** It reaches 94.7% of peak dense-GEMM energy
   efficiency on our workload `[M]`. There is no workload-specific inefficiency to harvest.

---

## 1. The whole question reduces to one ratio, because energy binds first

Four bounds gate a control chunk, and latency is the largest of them:

```
t = max( t_compute , t_memory , t_comm , E_chunk / (TDP · (1 − f_static)) )
```

The fourth term exceeds the others by roughly an order of magnitude in our model `[S]`. A
chunk costing `E` joules cannot complete faster than `E` divided by the watts available,
whatever the peak TOPS says. This is why the RPU's 4 PFLOPS FP4 peak `[T]` is not the
interesting number: at 40 W it would imply 100 TFLOP/W, which no silicon achieves.

**When both chips are scored at the same power ceiling, the TDP ratio cancels and speedup
equals efficiency exactly: S = η.** We score ourselves at 40 W, the same ceiling we grant
Thor, so we never win on a larger power budget. The design target of 3.0× additionally
survives granting the baseline 50 W — a 25% thermal advantage `[S]`.

This is also why the memory wall cannot be assumed away. 14B weights at 4 bits is ~7 GB,
which never fits head-power SRAM (90 MB in the current design point), so weights stream from
DRAM every step under both DreamZero and JEPA. See [`MEMORY_BANDWIDTH.md`](MEMORY_BANDWIDTH.md).

---

## 2. η is a ratio of overhead fractions, not a claim about better multipliers

Write `f` for the fraction of a chip's energy that reaches its multipliers. Then

```
η  =  (arithmetic energy ratio)  ×  (f_ours / f_gpu)
```

**The first factor is approximately 1, and this kills the three differentiators the project
used to claim.** Blackwell has native FP4 and FP8, so low-bit arithmetic is already in the
baseline. FlashAttention-class fusion is what our own measured anchors ran. Near-zero
instruction-fetch overhead has been TPU-standard since 2015. **We are not claiming a cheaper
multiply; we are claiming a cheaper delivery of operands to it.**

So η reduces to `f_ours / f_gpu`, and the entire bet is that a fixed-function, statically
scheduled datapath delivers a larger share of its joules to arithmetic than a GPU does.

---

## 3. Measured evidence on the baseline

### 3a. What the GPU actually costs per FLOP

`scripts/measure_fu_fraction.py`, RTX PRO 6000 Blackwell, results in
`fixtures/crosscheck/rtx_pro_6000_fu_fraction.json` `[M]`:

| Configuration | Best result | At |
|---|---|---|
| Dense GEMM, BF16, L2-resident | **1.480 pJ/FLOP** raw, 1.298 marginal | n=4096, 405 TFLOP/s |
| Dense GEMM, FP8 E4M3 | **0.956 pJ/FLOP** raw, 0.839 marginal | n=8192, 628 TFLOP/s (corrected 2026-08-05) |
| Our workload (3-step CFG, N=3120) | **1.562 pJ/FLOP** | 384 TFLOP/s |
| Idle, clocks up | 73.7 W | — |
| DRAM stream | 1461–1464 GB/s | **81.6% of the 1792 GB/s spec** |

**Interpretation.** A dense GEMM is the most arithmetic-dense kernel this silicon can run, so
its energy per FLOP bounds multiplier energy from above. That yields `f_gpu ≤ 73%` raw, which
is true and nearly useless — a GEMM still pays for register files, L2, warp scheduling, clock
and leakage. The useful result is the comparison at equal precision: **1.562 against 1.480
means our workload achieves 94.7% of peak GEMM efficiency.**

**That result is unfavourable and it retires an argument.** We had claimed batch-one inference
over an 18,700-token context is worst-case for GPU reuse, implying depressed `f_gpu` and free
headroom. It is not. Whatever η we earn must come from overhead present in the GPU's *best*
case, not from the GPU handling our workload poorly.

### 3a-bis. What the baseline actually is, and why it flatters us

**Measurement boundary.** `nvidia-smi power.draw` reports **GPU board power** — it excludes
the host CPU, system memory and PSU losses. Defensible for a chip-to-chip comparison, but it
is not wall power and the fixtures do not currently say so.

**Baseline selection, and this is the load-bearing caveat.** The RTX PRO 6000 Blackwell is a
600 W workstation card optimised for throughput with a wall socket behind it. Thor is
optimised for perf/W at 40-130 W. **Of the whole Blackwell family we characterised the member
with the least incentive to be efficient**, then used it to define "what a GPU costs per
FLOP." Three consequences, all unfavourable to our numbers:

1. **`f_gpu` = 3-13 % describes the RTX, not Thor.** Thor's functional-unit fraction is
   higher by design, so eta against Thor is *smaller* than eta against this anchor.
2. **The 600 W clamp caps the measured arithmetic ceiling.** FP8 measures 628 TFLOP/s
   (corrected 2026-08-05) against a much higher unconstrained-capability spec, because watts
   bind. So 0.956 pJ/FLOP is what the part achieves *while power-limited*, not the
   architecture's floor. The true floor is lower, which shrinks eta again.
3. **The calibration is fitted entirely to this one part.** All four anchors are RTX PRO 6000;
   `compute_util = 0.8048` and `e_flop_fp4_pj = 0.3565` were solved against a wall-powered
   workstation GPU and are then applied to Thor and to the RPU.
   [`PREDICTIONS.md`](PREDICTIONS.md) already names cross-architecture transfer as "the
   assumption most likely to be wrong"; this is the concrete mechanism.

**What survives.** Every measurement remains valid *as a measurement* — DVFS flatness, the
600 W clamp, 81.6 % achieved bandwidth, the roofline positions, the 94.7 %-of-GEMM result.
What does not survive is using any of them to characterise **Thor**. The ~2.6x central
estimate does not rest on them: 7c rebuilt it on Thor's published spec precisely because the
RTX comparison was unsound.

### 3b. Bounding f_gpu

With the workload measured at 1.562 pJ/FLOP, `f_gpu` depends on one remaining literature
term: the energy of a raw BF16 multiply-accumulate at N4, roughly 0.05–0.20 pJ/FLOP `[X]`.

| MAC energy `[X]` | f_gpu | Ceiling 1/f_gpu | f_ours needed for η = 2.15 |
|---|---|---|---|
| 0.05 pJ/FLOP | 3.2% | 31× | 6.9% |
| 0.10 pJ/FLOP | 6.4% | 16× | 13.8% |
| 0.15 pJ/FLOP | 9.6% | 10× | 20.6% |
| 0.20 pJ/FLOP | 12.8% | 7.8× | 27.5% |

**`f_gpu` is 3–13%, centred near 6–8%.** Pure overhead removal is therefore capped at roughly
8–31×, which is why a bottom-up ledger that returned 29–55× (`sim/energy.py`, since removed) was always a
defect rather than a discovery. Clearing the 2.15 bar requires `f_ours ≈ 7–28%`, centred near
14%.

**Do not use this table as a predictor.** Propagating the same 4× spread forward gives η
anywhere from 0.9× to 10.9×. The bottom-up route is too sensitive to a term we cannot
measure, which is why §7 anchors on published whole-architecture results instead.

### 3c. Earlier measured anchors

Four anchors on the same board, reproduced by the calibrated model within **0.5–3.9% on
latency and 0.8–2.5% on energy** `[M]`. Each runs BF16 and lands at 364–384 TFLOP/s and
1.562–1.648 pJ/FLOP — consistently just under the 405 TFLOP/s dense-GEMM ceiling, which is
the physical sanity check that later exposed a 2× FLOP-counting error in an agent's analysis.

Two further measured results constrain the design:

- **DVFS buys ~1.0×.** Energy per FLOP is flat from 1.0 to 3.1 GHz after subtracting idle
  `[M]`. A GPU cannot go sub-Vmin because its SRAM, cell libraries and clock distribution pin
  it at its floor.
- **FP16 → FP8 delivers 1.77×, not 2×** `[M]`, from the DVFS sweep. A conflicting 1.24×
  from the fu-fraction harness was recorded here as an open discrepancy for a day.
  **Resolved 2026-08-05: the 1.24× was a harness artifact** — the FP8 kernel's operand
  layout prep (`b.t().contiguous().t()`) executed *inside* the timed loop, adding a 128 MB
  copy per iteration and depressing FP8 throughput 30 %. With the copy hoisted, the two
  instruments agree at the same shape to **0.5 %** (1.76× vs 1.768×). Recording the
  contradiction instead of picking a side is what made it findable; the fix predicted the
  corrected throughput before re-measuring (~650 predicted, 628 observed).

### 3d. Calibration state, stated honestly

The P6 gate is GREEN, and the fit is **not identified**. Two of four coefficients rest on
their box bounds and `rpu/report.py` prints them as UNIDENTIFIED:

| Coefficient | Fitted | Status |
|---|---|---|
| `compute_util` | 0.8048 | identified |
| `e_flop_fp4_pj` | 0.3565 | identified |
| `bw_util` | 1.0000 | **pinned at bound — and now refuted at 0.816** `[M]` |
| `e_byte_hbm_pj` | 64.0 | **pinned at bound** |

A passing gate is not identification (lesson L2). Today's streaming measurement gives
`bw_util ≤ 81.6%`, since a contiguous copy is the best case and a scattered workload does
worse. **The fitted 1.0000 is unattainable.** We deliberately did not fold this back into the
solver: it shares no assumptions with the least-squares fit, which makes it worth more as an
independent cross-check (lesson L5). Refitting is a separate, explicit decision.

---

## 4. Where the energy goes, and why f_ours ≈ 35% is harder than it sounds

Measured accelerator silicon says arithmetic is a small minority of chip energy:

| Source | Multipliers | Clock network | Memory / registers |
|---|---|---|---|
| Eyeriss, fabricated 65 nm `[X]` | **3.0–8.9%** | **32.9–45.0%** | scratchpads 33–42% |
| Eyeriss v2, post-layout `[X]` | 2–9% | 20% → **55%** as utilization falls | SPads ~72% of PE area |
| Simba, measured 16 nm `[X*]` | 11.2% of PE area | — | buffers 71% of PE area |
| Hameed, ISCA 2010 `[X]` | 10% to functional units | pipeline+clock 22% | caches 19%, RF 10% |

Verbatim from Eyeriss: *"the ALUs only account for less than 10% of the total power"* and
*"Besides the clock network, the spads dominate."* The clock share **triples as effective
utilization falls**, and batch-one decode is exactly that regime.

**The gate-1 criterion of `f_ours ≥ 35%` is more ambitious than any purpose-built DNN ASIC has
published.** Hameed's ladder tops out near 35% for fused custom datapaths, and we wrote our
gate from that *ceiling*. Two consequences:

- The criterion is **stricter than η requires** (§3b: 14% suffices for the 2.15 bar). It
  should not be used to kill a design point that would have cleared the bar.
- The realistic target is `f_ours ≈ 15–25%` — meaningfully above Eyeriss and Simba, well below
  Hameed's ceiling. Our advantage over Eyeriss is structural: no per-PE scratchpads, and adder
  trees that attack the register/clock bucket directly (§5).

---

## 5. The design consequences

### 5a. Adder-tree register amortisation is a feasibility gate, not an optimisation

In a naive weight-stationary systolic PE every MAC owns pipeline registers — an activation
register forwarded to its neighbour and a partial-sum accumulator updated every cycle — and
both are clocked every cycle. Combining N products in a **combinational adder tree** and
updating **one accumulator per N MACs** leaves the multiply narrow while touching the wide
accumulator 1/N as often.

Sizing against the current design point, 1.90 M MACs at 1.05 GHz against a ~19 W fabric
budget `[T]`:

| Register style | Clocked bits/MAC | Register + clock power |
|---|---|---|
| Naive flop-per-MAC systolic PE | 40 | **32–120 W (168–630% of budget)** |
| FP4, 24-bit psum, 1 reg/MAC | 28 | 22–84 W (118–441%) |
| **FP4 + 8-wide adder tree** | **7** | **5.6–21 W (29–110%)** |
| FP4 + 16-wide tree + BF16 accum | 5 | 4.0–15 W (21–79%) |

**A conventionally pipelined array does not fit the power budget at all.** Shipped precedent:
TPUv4i replaced 128 serial two-input adders with four-input sums, saving **40% area, 25%
power, and 12% of MXU peak power** `[X*]`. The cost is combinational depth eating clock
frequency, which is close to free at 1.05 GHz and expensive for a high-clock part.

**Load-bearing unknown:** flop clock-pin and local-tree energy in the target PDK. That is the
single most valuable Tier-2 characterisation in the program, because the table above spans
"fits comfortably" to "impossible" across its plausible range.

### 5b. Array geometry decides where in the TPU band we land

Hardcoding the transformer buys less than it sounds, because the operator set and static
dataflow are already what §2's eta describes. What the fixed function *enables* is a free
choice of array geometry, and our own sweep says that choice is first-order `[S]`:

| Array | MACs/cycle achieved / peak | Geometric utilization |
|---|---|---|
| 64x64 | 3,345 / 4,096 | **81.7%** |
| 128x128 | 11,078 / 16,384 | 67.6% |
| 256x256 | 29,113 / 65,536 | **44.4%** |

**The mechanism is pipeline fill and drain, not shape mismatch.** Both target models have
head_dim exactly 128 (5120/40 and 1536/12), so shapes divide cleanly. The loss comes from
`pass_cycles = S + rows + cols - 2`: a 256x256 array burns 254 cycles per pass regardless of
work done, which is **49.9% of a 512-long stream and 14.0% of a 3120-long one**.

**This is a self-inflicted loss, not an advantage over the baseline.** The GPU measures
94.7% of peak GEMM efficiency on this workload (§3a); its tensor cores use small tiles and
barely pay this penalty. Choosing geometry well recovers ground we would otherwise give
back — it does not create an edge. Concretely: fine-grained geometry places us in the upper
half of the published 1.6-3.2x band, and a 256x256 array places us at or below its bottom.

**Counterweight, and the reason this is not yet a recommendation.** `design_space.py`
states that it does not model NoC, load imbalance across arrays, or bank conflicts, and all
three worsen as arrays multiply: 1.9 M MACs needs ~465 arrays at 64x64 against 29 at
256x256, and the sweep scales the fleet linearly while flagging that as optimistic. The
optimum is interior and the model cannot currently find it. **Adding an interconnect and
imbalance term (roadmap phase 4.5, unbuilt) is the highest-value simulator work remaining**,
because without it array sizing is a guess.

### 5b. What else follows

| Decision | Why, from the evidence above |
|---|---|
| Systolic weight-stationary array, no per-PE scratchpads | Eyeriss spends 33–42% of power on scratchpads; that is the bucket to delete |
| Static compile-time schedule, no dynamic scheduling | Removes the control silicon Hameed measures at 10%, and enables §6 droop shaping |
| Large banked SRAM (90 MB) with fused attention | The unfused attention score matrix is 233 MB per head per layer; fusing is worth **56.7×** on attention traffic `[S]` |
| Low-bit weights, bit-exact control path | Weights stream 7 GB/step regardless; and the control policy must not depend on aggressive quantization `[F]` |
| Target ~1.05 GHz, not 2.5 GHz | Permits denser, lower-drive cells and a shallower pipeline; makes the adder tree free |

---

## 6. Levers evaluated and rejected

Three research streams evaluated roughly forty techniques. **Nothing additive survived at
scale.** Full detail in [`PERF_LEVERS.md`](PERF_LEVERS.md) Ledgers D4–D6.

**Pursue.** Adder-tree amortisation (§5a, feasibility). Latch-based design with time
borrowing, converting ~25% frequency headroom into lower Vdd at fixed throughput `[X*]` —
the one candidate attacking the DVFS wall with no model-side change. Canary/CPM adaptive
voltage scaling, which shipped in POWER7 for **−20 to −24% chip power** at 0.2% area `[X*]`.
Droop-aware static scheduling at 6–10% of logic power. Multi-Vt and body bias. Moderate
undervolting to ~0.55–0.6 V with a 2–3× wider array, worth **1.4–1.7× on logic** and
**1.15–1.25× at system level** after LPDDR5X dilution `[X*]`.

**Rejected, each with its reason recorded once so it is not reopened.** Alternative number
systems (LNS measured *worse* than INT8; L-Mul → 0 on an ASIC). Compute-in-memory (density,
not weight residency). Razor-class timing speculation (energy-negative per inference; replay
means variable latency against a deadline proof). Voltage stacking (912 mm² of regulator to
make reliable). Integrated voltage regulators as efficiency. FD-SOI and body bias at N4.
LC resonant clocking (needs ~23× the inductance at 1.05 GHz and **detunes under clock
gating**, our main lever). Low-swing clocking. Clock mesh. Wave pipelining. Adiabatic logic.
Full asynchronous. Approximate/noise-tolerant MAC (model-specific, and unsafe for a control
policy).

**One rejection matters for integrity.** Eyeriss's widely-cited 45% zero-operand-gating saving
is measured against an *ungated* baseline on ReLU CNNs with 77.6% zeros. Transformers have
essentially none. **Citing it would credit the design under test with sparsity the workload
does not have, violating the one-utilization-model invariant.** Honest value at our zero
rates: 2–3% of dynamic power for 5.7% area. Rejected.

**Escalated, not decided.** Backside power delivery is worth **15–20% at iso-speed** `[X*]` —
the largest single number in the domain — and does not exist at N4/N5 or at TSMC N2/N2P. It
is available on Intel 18A now and TSMC A16 in 2026–27. This is a roadmap fork. The thermal
caveat is specific to us: backside power moves transistors away from the heat path, and the
head is fanless.

---

## 7. The composite, and why it sits where it does

**η, architecture: 2.2×, range 1.8–2.8.** We anchor on TPUv4's published **1.6–3.2×** over a
same-node A100 `[X]` rather than on the bottom-up ratio, because §3b's spread is too wide to
predict with and this project has a documented history of bottom-up ledgers returning absurd
answers. Nothing in three research streams produced a mechanism to exceed that band. We are
claiming competent execution of a proven architecture class, not new physics.

**Physical design: 1.2×, range 1.15–1.4 at system level.** Sub-Vmin contributes 1.4–1.7× on
the logic term, diluted by LPDDR5X and its PHY which run at a fixed rail and cannot be
voltage-scaled at all. Explicitly **not counted in the 2.05/2.15/3.0 bars**; gate is a
test-structure tile on the gate-4 shuttle.

**Composite ~2.6×, range 2.1–3.2.** Against a 2.15 bar and a 3.0 target.

**Confidence ~50%.** It rose modestly today because one side of the `f_gpu` ratio became
measured rather than estimated, and because `bw_util` moved from pinned-and-unidentified to
measured. It did not rise further because the 94.7%-of-GEMM result retired a favourable
argument, and because every technique that would have been additive turned out to be
baseline parity or too small.

### Known asymmetries, both directions

**Three favourable terms are currently priced at 1.0, and that is a bias, not caution (added
2026-08-04 after challenge).** Each is real, sized, and measurable:

1. **Thor's 40 W includes silicon we do not carry.** It is an SoC — 14-core CPU, ISP, codecs,
   PVA, 4x25GbE — while our host lives outside the head budget by declared architecture. If
   Thor's uncore burns 8-15 W of its 40, its compute budget is 25-32 W against our 40:
   a **1.25-1.6x** term the model ignores by granting both rows identical ceilings `[T]`.
   Measurable on any Jetson: idle and uncore power in the constrained mode.
2. **The TPU anchor was measured in the GPU's best regime.** TPUv4's 1.6-3.2x is against an
   A100 at datacenter batch under mature CUDA — maximum amortization. Batch-one with a hard
   deadline is the GPU's *worst* regime. The band is closer to a floor for our comparison
   than a prediction `[X]/[T]`.
3. **The compiler derate was applied to us and not to them.** TensorRT's assumed 75-85 %
   extraction is earned on CNNs and LLMs at batch; on batch-one FP4 video-diffusion models —
   months-old NVFP4 workflows, nobody's tuned path — it may be nearer 60 %, returning most of
   the 1.4x launch derate we charged ourselves `[T]`. Measurable in the Orin benchmark by
   profiling achieved-vs-peak on the frozen workload.

Compounded at modest values these move the central estimate from 2.6-3.0x to **3.5-4.5x** and
put first silicon above the 2.15 bar rather than below it. They are held out of the headline
because each is unmeasured — but they are recorded here so the conservatism is visible rather
than silent, and so the Orin measurement can price the first and third directly.

*Also favouring us:* our static schedule owes no misprediction guardband.

*Against us:* Thor is a 2025–26 part built for this exact market with native FP4. Our
accelerator needs a host we have not accounted for. Pre-silicon estimates in this domain carry
a documented **~3× simulation-to-silicon gap** (9.3× simulated versus 3.3× measured for
near-threshold operation `[X*]`), and everything in §5 and §6 is pre-silicon.

---

## 7b. Arithmetic, not memory, is the binding term — and the accumulator decides feasibility

**Corrected 2026-08-04, same day, after the first version of this section was wrong.** The
original used 0.05 pJ/FLOP — a *BF16* multiplier cost — as the arithmetic floor for an *FP4*
chip. Multiplier energy scales roughly with the square of operand width, so FP4 is ~16x
cheaper at the multiply, and that substitution understated the ceiling by an order of
magnitude. It produced the claim that the requirement "exceeds the physical ceiling by 4.5x
even granting a perfect chip," which is false. Corrected figures below.

### The budget

Regenerated from `forward_per_step` at FP4 weights / FP8 activations, 3 diffusion steps with
CFG, N=3120 `[S]`. Chunk budget is 8.00 J (40 W at 5 Hz) for 7.107e14 FLOP and 45.9 GB of
DRAM traffic.

| Term | Energy | Share of the 8.00 J budget |
|---|---|---|
| All DRAM traffic at 32 pJ/B (4 pJ/bit, best-case LPDDR5X) | 1.47 J | **18%** |
| All DRAM traffic at 64 pJ/B (8 pJ/bit — the fitted e_byte) | 2.94 J | **37%** |
| FP4 multiply only, 0.0078 pJ/FLOP | 5.54 J | **69%** |
| FP4 MAC with adder-tree amortised accumulate, 0.0126 pJ/FLOP | 8.92 J | **111%** |
| FP4 MAC with a naive 32-bit accumulator RMW, 0.0178 pJ/FLOP | 12.65 J | **158%** |

**Two findings, and the second is the actionable one.**

*Memory and arithmetic are BOTH first-order energy terms — corrected 2026-08-06.* An
earlier version of this table priced DRAM at "5 pJ/B", a pJ/bit-class figure used as
pJ/byte — the exact 8x landmine design F1 documents — and concluded DRAM was 3-6% of the
budget. At LPDDR5X system energy (4-8 pJ/bit = 32-64 pJ/byte, consistent with the fitted
e_byte of 64 the calibrated model has used all along), **DRAM is 18-37% of the chunk
budget**. The calibrated model, the bars and eta were never affected — they always used
the fitted value; the error lived in this budget table and the explorer's budget panel. **An earlier version of this section
concluded "the memory wall is not the wall". That was wrong**: it answered a bandwidth claim
with an energy argument. Memory binds on *time*, and 7d shows it binds hard.
[`MEMORY_BANDWIDTH.md`](MEMORY_BANDWIDTH.md) was right.

*The accumulator determines whether the arithmetic fits at all.* 69% versus 158% is the
entire difference between a multiply-only datapath and one that reads, modifies and writes a
32-bit accumulator every cycle. **This makes 5a's adder tree a feasibility gate in a
stronger sense than that section argues** — not a 2.1x optimisation on arithmetic energy,
but the term that decides whether arithmetic alone busts the budget.

### The ceilings, corrected

Absolute 5 Hz at 40 W requires **0.0113 pJ/FLOP all-in — 88.8 TFLOP/W sustained.**
Stated in absolute units on purpose: an earlier draft expressed this as a ratio against the
measured RTX, and a ratio against the *calibration anchor* is too easily misread as the
multiplier against *Thor*, which is a different number answering a different question.

| Our chip at | All-in pJ/FLOP | Sustained TFLOP/W | Work reduction still needed |
|---|---|---|---|
| Architectural ceiling (f_ours 20 %, no compiler derate) | 0.030 | 33.3 | **2.7x** |
| Mature (compiler 0.80) | 0.038 | 26.7 | **3.3x** |
| First silicon (compiler 0.55) | 0.055 | 18.3 | **4.8x** |

**The gap is closable.** A realistic chip falls 4.4-5.6x short of the absolute goal, and that
is the magnitude the work-reduction levers supply — conditional compute alone is 3-4x, and it
composes with step reduction and cross-chunk reuse. This is consistent with the repo's
existing position that absolute 5 Hz at 40 W needs model-side compression.

### What that implies for the program

Work reduction composes with eta rather than competing with it:

| Lever | Worth | Note |
|---|---|---|
| **Conditional compute / MoE** — 14B total, 2-4B active | **3-4x** on arithmetic *and* weight traffic | Largest unexploited lever. A model decision, not a chip one, and it does not touch the no-aggressive-quantization constraint `[F]`, which governs numerics rather than routing |
| Step reduction, 3 -> 1 | up to 3x | 16 -> 3 already done |
| Cross-chunk receding-horizon reuse | 2.3x at 99.4% quality | Already Ledger B flagship |
| Token count (N=3120 is a choice) | linear | |
| Asynchronous hierarchy: cheap policy at 5 Hz, world model at 1 Hz | decouples the deadline from the big forward pass | Unexplored |

**The chip is the minority of the win**: it closes the gap to within 2.7-4.8x, and the
remainder comes from the model and the schedule. The moat statement in
`VC_CHEATSHEET.md` (*"the moat is the system"*) is the engineering reality, not modesty.

**Keep the two questions separate.** This section is about *absolute* feasibility against a
workstation GPU baseline. Competitiveness against Thor at equal head power is the separate
eta question of 7, and the two numbers are not interchangeable.

---

## 7c. The bet, restated as one measurable number: Thor's achieved fraction of peak

**This supersedes the framing in 3b.** `f_gpu` is hard to measure and needs a PDK to pin
down. The same bet expressed against published Thor specs needs only a benchmark.

| | TFLOP/W |
|---|---|
| Thor, **peak**, FP4, from spec (2070 TFLOPS / 130 W) `[X]` | **15.9** |
| Our chip, **sustained**, at f_ours = 20-25% and 0.0125 pJ/FLOP FP4 arithmetic `[T]` | **16-20** |

**We are claiming to sustain what Thor can only peak at.** Everything then turns on Thor's
realized fraction of peak on this workload:

| Thor achieves | Our advantage | Against the bars |
|---|---|---|
| 50% of peak | 2.0-2.5x | at or below the 2.15 solid bar |
| 35% of peak | 2.9-3.6x | clears comfortably |
| 20% of peak | 5.0-6.3x | exceeds the 3.0 target |

The 2.05 / 2.15 / 3.0 bars correspond to Thor landing at roughly 40-50% of peak.

**The warning sign points to the unfavourable end.** Our own measurement (3a) shows the RTX
achieving **94.7% of peak dense-GEMM efficiency** on this workload. GPUs are not struggling
with it. If Thor lands above 50% of peak, we graze the bar rather than clear it.

**A comparison retired.** An earlier draft claimed 25-31x against the measured RTX. That
mixed FP4-projected-sustained against BF16-measured-achieved -- precision and peak-vs-achieved
compounding. Discard it; the Thor comparison above is the defensible one.

**A baseline clarification.** Published comparisons of Thor against the RTX 6000 **Ada**
(300 W, Ada Lovelace) do not describe our anchor. We measure an RTX PRO 6000 **Blackwell**
at 600 W -- the same architecture generation as Thor, with native FP4. Do not carry the
~1.4x normalized Ada figure into any of our numbers.

**Framing correction, and it matters.** Do not measure "fraction of peak." 1 established
that peak throughput is not what binds — energy is — and expressing the experiment against
peak smuggles the wrong reference back in. **Measure achieved joules per chunk on the frozen
workload.** Thor's 15.9 TFLOP/W is an *upper bound* on its achieved efficiency, useful as a
sanity ceiling and nothing else. The table above uses fraction-of-peak only to bound the
answer from published specs while the measurement does not exist.

The measurement is already specified: [`PREDICTIONS.md`](PREDICTIONS.md) seals **59.1 ms and
2.68 J per forward pass** for Orin. Joules, not a fraction of anything.

### The achievable range, and where the risk actually sits

| Scenario | Our chip `[T]` | vs Thor at 30 / 40 / 50 / 70 % of peak |
|---|---|---|
| Realistic — f_ours 20 %, adder tree, x1.2 physical | 19 TFLOP/W | 4.0x · **3.0x** · **2.4x** · 1.7x |
| Optimistic — f_ours 25 %, x1.3 | 26 TFLOP/W | 5.5x · 4.1x · 3.3x · 2.3x |
| Ceiling — f_ours 35 %, x1.4 | 39-49 TFLOP/W | 8-10x · 6-8x · 5-6x · 4x |

**~2.6x expected, ~5-6x if everything breaks right, ~1.7x if Thor is more efficient than we
assume.** The ceiling row requires beating every published DNN ASIC on functional-unit
fraction (Eyeriss 3-9 %, Simba ~11 %, Hameed's 35 % a never-reached ceiling) *and* Thor
landing at 30-40 % of peak. Not a plan.

**The bottom-right cell is the program's largest risk: at 70 % we miss the bar outright.**
That is not a tail scenario — 3a measured a GPU hitting 94.7 % of peak dense-GEMM efficiency
on this very workload. It is unmeasured for Thor.

**Consequence: the priority ordering is forced.** The uncertainty is two-dimensional --
our `f_ours` and Thor's achieved efficiency -- spanning 1.7x to 13x. One axis needs a board
and an afternoon; the other needs a PDK. **Measure Thor (or Orin as proxy) first.** This
supersedes earlier statements in this document that `f_gpu` was the highest-value measurement.

---

## 7d. Roofline position, and why the RTX measurement does not transfer to Thor

**The regimes are not comparable, and this retires the "warning sign" in 7c.**

| Part | Ridge point (FLOP/byte) | Workload intensity | Margin above ridge |
|---|---|---|---|
| RTX PRO 6000 @ BF16 | 279 | 5,315 | **19x** — deep in compute-bound territory |
| Thor @ FP4 | 7,582 | 15,498 | **2.0x** |
| **RPU @ FP4** | **13,021** | 15,498 | **1.19x — essentially on the ridge** |

Our 94.7 %-of-peak-GEMM measurement (3a) was taken **19x above the ridge**, where there is
nothing to stall on. Thor operates at 2x and our own chip at 1.19x. **Inferring Thor's
achieved efficiency from that measurement is invalid**, and the earlier claim that it points
to the unfavourable end of 7c's table is withdrawn.

### Applying the MEASURED bandwidth utilization changes who is feasible

The workload needs **229 GB/s sustained** at 5 Hz (45.9 GB per chunk, FP4 weights). Using the
81.6 % utilization measured today `[M]` rather than the fitted `bw_util = 1.000`:

| Part | Spec | At 81.6 % | Headroom vs 229 GB/s |
|---|---|---|---|
| **Thor** | 273.0 GB/s | 222.8 GB/s | **-2.7 % — memory-bound** |
| **RPU** | 307.2 GB/s | 250.7 GB/s | **+9.5 %** |

**SCOPE — corrected on review. This section is about the ABSOLUTE 5 Hz goal, not the 40 W
head-to-head.** At 40 W the chunk takes 0.7-2.2 s, so sustained bandwidth needed is only
15-67 GB/s against 220-250 GB/s available: **neither part is memory-bound at head power, both
are energy-bound.** Worse for the optimistic reading, Thor's ridge point *falls* from 7,582 to
**2,333 FLOP/byte** when power-limited to 40 W (peak scales with power, bandwidth does not),
placing the workload **6.6x above its ridge** — further into compute-bound territory, not less.
An earlier version of this section claimed the memory-bound result "materially reduces the
program's largest stated risk". **It does not**: it constrains Thor's ability to reach 5 Hz,
which is a separate question from its efficiency at 40 W.

**Two consequences, pointing in opposite directions.**

*Favourable, for the absolute goal only:* **Thor cannot stream weights fast enough for 5 Hz**
even before energy is considered.

*Unfavourable:* **the RPU's 9.5 % headroom is dangerously thin.** Any traffic-model error or
scattered-access penalty puts us memory-bound too. And the 81.6 % figure came from a
*contiguous copy on HBM* — the best case on the friendlier memory technology. LPDDR5X under
real access patterns will do worse for both parts, which erodes our margin faster than Thor's
deficit.

### What follows

- **The RPU's 307 GB/s looks under-provisioned.** Revisiting it is cheaper than anything in
  the energy ledger and should be an explicit design-point decision rather than an inherited
  constant.
- **Conditional compute / MoE moves from "largest unexploited lever" to "the thing that makes
  the design close."** It is the only lever that cuts weight traffic *and* arithmetic by 3-4x
  simultaneously, and we are 9.5 % from the bandwidth wall and ~4x from the energy budget.
- **A memory-bound anchor is now a gating measurement, not a nice-to-have.** Everything above
  rests on an 81.6 % figure measured on HBM with contiguous access. The LPDDR scattered-access
  number is what actually decides feasibility for both rows.

---

## 7e. First-principles derivation — an independent route to the same answer

Derived without using TPUv4's band, our RTX anchors, or any published speedup, so it shares
no assumptions with 7 (lesson L5).

**One identity does the work.** `eta = Thor pJ/FLOP / our pJ/FLOP`, and `our pJ/FLOP =
arithmetic / f_ours`. Thor's peak is a hard published number — 2070 TFLOPS / 130 W =
**0.0628 pJ/FLOP** `[X]` — so the same arithmetic primitive that sets our floor *also* fixes
Thor's own overhead fraction. It is the hinge, not a free parameter:

| FP4 MAC cost | Implies Thor's f | eta at f_ours = 20 % | Ceiling at f_ours = 35 % |
|---|---|---|---|
| 0.0031 pJ/FLOP — Horowitz int8 scaled 45->4 nm | 5 % | **4.0x** | 7.0x |
| 0.0063 — x2 for FP format overhead | 10 % | **2.0x** | 3.5x |
| 0.0125 — CHIP_SPEC 6 with adder tree | 20 % | **1.0x** | 1.8x |
| 0.0178 — CHIP_SPEC 6 with 32-bit accumulate | 28 % | **0.71x** | 1.2x |

**Taken at face value, CHIP_SPEC's own MAC cost kills the project**: it would put Thor at
20-28 % functional-unit fraction against a best-ever published ceiling of 35 %, leaving
nothing to take.

**The high-MAC rows are excluded by consistency, not by preference.** Thor's 0.0628 pJ/FLOP is
*module-level*, including a 14-core ARM CPU, memory controllers and I/O. If the tensor cores
draw half the 130 W, the tensor-core-only figure is ~0.03 pJ/FLOP, and a 0.0125 MAC would put
Thor at **43 %** — above Hameed's ceiling, which no fused custom datapath has ever reached and
which a programmable GPU with caches, register files and dynamic scheduling certainly has not.
Running it backward, a programmable GPU plausibly sits at f <= 10 %, forcing **arithmetic
<= 0.006 pJ/FLOP** and selecting the top two rows.

**Result: eta = 2.0-4.0x, central 2.6-3.0x, ceiling 3.5-7x at Hameed's 35 %.** The same answer
as 7, by a route sharing none of its inputs.

### The accounting, redone (2026-08-05) — the kill-row was a double count

Tracing CHIP_SPEC 6's 0.0156 pJ to its source settles the hinge's worst case: it is
Accelergy's 3.0 pJ **16-bit INT MAC — accumulate included** — scaled by (4/16)^2 /12.
Calling that a "multiply" and adding a 0.020 pJ accumulator on top counted accumulation
twice, and the quadratic width rule was applied at INT width 4 when an **E2M1 multiply has
a 2-bit significand**. Redone from Horowitz 45 nm primitives (2bx2b significand multiply +
3b exponent add + normalize; node scaling /8 to /12) `[X]/[T]`:

| Term | pJ/FLOP at ~4 nm | Thor implied f | eta at f_ours = 20 % |
|---|---|---|---|
| Multiply only | 0.0016-0.0024 | 2.6-3.9 % | 5.2-7.9x |
| **+ 8-wide adder tree accumulate** | **0.0038-0.0057** | **6.0-9.1 %** | **2.2-3.3x** |
| + naive 32-bit accumulate | 0.0058-0.0087 | 9.2-13.8 % | 1.4-2.2x |

**Three consequences.** The 7e table rows at 0.0125-0.0178 are superseded — the tension
"CHIP_SPEC's face value kills the project" dissolves, because the face value was a double
count. The central estimate is *reinforced, slightly favourably*: tree-accumulate
arithmetic gives eta 2.2-3.3x at f_ours = 20 % without touching Thor's slider. And 7b's
budget figures shrink the same way: chunk arithmetic with tree accumulation is **2.6-3.8 J
= 32-48 % of the 8 J budget**, not the 111 % previously stated — arithmetic alone no
longer busts the budget, though a naive 32-bit accumulator (~47-77 %) still roughly
doubles it, so **the adder tree remains the decision between comfortable and marginal**
rather than between possible and impossible.

**The boundary caveat, stated because it cuts against us.** These are bare-datapath
numbers. The same method applied to BF16 implies the measured RTX runs at f ~ 1.1-1.6 % —
*below* the 3 % Eyeriss floor used by the consistency guards. The implied-f band therefore
depends on where the "datapath" boundary is drawn (bare arithmetic here; arithmetic plus
local operand registers in the Eyeriss-derived floors). The guards remain valid as
*relative* checks; absolute f comparisons across boundary conventions are not meaningful,
and this is now the sharpest remaining softness in the first-principles route.

### This changes which measurement matters most

Earlier sections named `f_gpu` and then Thor's achieved joules as the critical measurement.
**First principles says it is neither: it is the energy of an FP4 multiply-accumulate at the
target node.** That one number sets our floor and Thor's overhead fraction simultaneously, and
it is currently uncertain by 6x within our own spec. Resolving
[`CHIP_SPEC.md`](CHIP_SPEC.md) 6's MAC accounting — including whether its 0.0156 pJ multiply
correctly reflects an E2M1 format with a one-bit mantissa — is now the highest-value
analytical work in the program, and unlike the others it needs a datasheet and an afternoon
rather than a PDK.

---

## 7f. The compiler-maturity derate — a real term we do not price

**Our fairness invariant says both rows run the identical model graph. It does not say both
rows run equally good software, and they will not.** Thor arrives with CUDA, cuDNN, TensorRT,
JetPack, PyTorch and Isaac ROS — on the order of fifteen years and thousands of engineer-years
of kernel tuning, and a robotics team can go from a PyTorch checkpoint to an optimised
deployment in days. We arrive with a version-one compiler.

**The derate is multiplicative and it lands directly on eta.** If TensorRT extracts 70 % of
what Thor's silicon can do and our first compiler extracts 50 % of what ours can, we lose
**1.4x** before any architecture argument is heard. That is over half the margin between the
2.15 bar and the 3.0 target, and **the model currently has no term for it** `[T]`.

**Our architecture makes this harder in one direction and easier in another.** Harder: a fully
static schedule has no dynamic recovery, so every tiling, allocation and DMA decision must be
right at compile time — a GPU can paper over a mediocre schedule with occupancy and caches,
and we cannot. Easier: the search space is one model family with known shapes, not arbitrary
graphs, so the compiler can be narrow and deep rather than general.

**What must exist before first silicon is useful**, in dependency order:

| Layer | Why it cannot be skipped |
|---|---|
| Graph import (ONNX / PyTorch export) | Without it no real checkpoint runs, and every number stays synthetic |
| Operator coverage for one model family | The long tail — norms, RoPE, activations, sampling — is where deployments die |
| Fusion + tiling + SRAM allocation | This *is* the architecture. Section 5's traffic numbers assume a compiler that achieves them |
| Static scheduler and µcode emitter | No dynamic recovery means the schedule is the product |
| Numerics toolkit: FP4 calibration, per-channel scales, accuracy gates | The no-aggressive-quantization constraint `[F]` has to be enforced by tooling, not by intention |
| Runtime: DMA, command submission, host sync | |
| Profiler that explains a missed deadline | A deadline-miss-rate target is unmeetable if misses are not attributable |
| Bit-exactness CI against a reference | The only defence against silent numerical drift |

**What we should deliberately not build:** a general-purpose compiler, a full framework
backend, multi-model support, or dynamic-shape handling. Every one of those is how a small
team loses two years, and none is needed for a module running one frozen model family.

### Sizing, and the staged eta that follows

**Industry pattern first: in this category the compiler fails, not the silicon.** Graphcore
shipped good hardware and lost on software; Wave Computing died on it; Groq narrowed its
market partly because arbitrary models were too hard to compile; Habana shipped with software
as the gating item for years. TensorRT and XLA each represent well over a hundred
engineer-years across roughly a decade `[X*, industry history, not a citation]`.

| Layer | Engineer-years to a good v1 `[T]` |
|---|---|
| Fusion, tiling, SRAM allocation, static scheduling — the hard core | **5-15** |
| Graph import + operator coverage, one family | 2-4 |
| Runtime, DMA, driver, host sync | 2-4 |
| Numerics toolkit and accuracy gates | 2-3 |
| Profiler that attributes a missed deadline | 2-3 |
| Bit-exactness CI | 1-2 |
| **Total** | **~15-30** |

At 5-8 software engineers that is **3-4 years — the same duration as the silicon.**

**The derate is not a separate term; it determines the realized `f_ours`.** Our architectural
ceiling only materialises if the compiler reaches it, and Thor's achieved efficiency already
includes TensorRT's maturity.

| Stage | Compiler extraction | eta |
|---|---|---|
| **First silicon, v1 compiler** | ~50-60 % of our ceiling vs TensorRT at 75-85 % of Thor's | **1.7-2.1x** |
| **Mature, ~2-3 years post-silicon** | 75-85 % | **2.6-3.0x** |
| Ceiling at f_ours = 35 % | — | 3.5-7x |

**The chip probably does not clear its own 2.15 bar on the day it powers on.** It clears it
when the compiler matures. Three consequences:

1. **Publish a launch number and a mature number separately.** A single figure invites a
   broken promise at the moment credibility matters most.
2. **The gate-1 kill criterion needs a stage attached.** Measuring eta at first silicon against
   a bar calibrated for maturity would kill a working design.
3. **Compiler headcount is the pacing item, not support.** Starting it when the RTL is done
   puts the mature number 3-4 years after tapeout instead of 2.

**Consequence for the program.** Software is not a downstream integration cost, it is a term
in eta. Two actions follow: price the derate explicitly as a Monte Carlo input rather than
leaving it at an implicit 1.0, and treat compiler headcount as competing with silicon
headcount for the same result rather than as support for it. `VC_CHEATSHEET.md` already lists
software as a top-three risk; this section is the quantitative version of that sentence.

---

## 8. What would falsify this

| Measurement | What it settles | Cost |
|---|---|---|
| Raw MAC energy at N4 | The one literature term left in `f_gpu`; collapses the 4× spread in §3b | Needs a PDK |
| Flop clock-pin + local-tree energy in the target PDK | Whether §5a's array fits at all | Needs a PDK |
| Jetson Orin against the sealed prediction in [`PREDICTIONS.md`](PREDICTIONS.md) | Whether coefficients transfer across architectures. Predicted 59.1 ms / 2.68 J, unmeasured, unedited since registration | Days, needs the board |
| Memory-bound anchor on a scattered access pattern | `bw_util` for real workloads, not just a contiguous copy | Hours |
| Reconciling 1.77× against 1.24× for FP16→FP8 | An open contradiction between two of our own measurements | Hours |

**Kill criteria remain as written** in [`CHIP_ROADMAP.md`](CHIP_ROADMAP.md): mapped η below
2.2, or `f_ours` below 35%, ends the program before tapeout money. §4 argues the second
criterion is stricter than η requires and should be restated; that is a proposal, not a change
made here.

---

## 9. Provenance and open gaps

**Measured by us `[M]`:** the four RTX anchors and their reproduction error; the DVFS
flatness; FP16→FP8 at 1.77×; today's GEMM ceiling, workload intensity, streaming bandwidth,
idle floor and 600 W clamp.

**External, primary opened `[X]`:** Eyeriss clock and ALU shares (verified against extracted
text); Hameed's overhead ledger; TPUv4's 1.6–3.2×; Leng's guardband decomposition.

**External, relayed and not personally verified `[X*]`:** Zimmer's 3.3× near-threshold result;
the Razor energy-negative curve; TPUv4i's adder-tree savings; POWER7's CPM numbers; TSMC A16
and Intel PowerVia figures. Labelled per lesson L10 rather than promoted.

**Open gaps, stated rather than filled:**
- No published clock-power share exists for any 7/5 nm dense datapath or AI accelerator, nor
  the tree-buffer / ICG / flop-clock-pin split at a modern node. §5a's table is `[T]`.
- The 1.77× versus 1.24× FP8 discrepancy is unexplained.
- `e_byte_hbm_pj` remains pinned at its bound and unidentified.
- No real checkpoint and no real Jetson have been measured. Every Thor number is projected,
  not measured, and the frozen benchmark contract records that distinction explicitly.
