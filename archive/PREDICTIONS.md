# Sealed predictions — pre-registered before measurement

The point of this file is to make the model **falsifiable**. Fitting a model to data and
then reporting the fit error is circular: of course it fits, it was tuned to. A prediction
written down *before* the measurement, and not touched afterwards, is a test.

**Rules.**
1. A prediction is recorded here **before** the corresponding hardware is measured.
2. Nothing in this file is edited after the measurement lands. The result is appended
   below it, including the error, whether the error is embarrassing or not.
3. The model is not tuned between writing the prediction and taking the measurement. If
   it is, the prediction is void and must be re-registered.
4. A large error is a finding, not a failure. Silence about one is a process defect.

Why this matters here specifically: our calibration has already demonstrated that a fit
will absorb missing physics into whatever coefficient is free rather than reveal it.
`e_byte_hbm_pj` reached 200 pJ/B, sixteen times any physical DRAM, and `bw_util` pinned
at 1.000, because those were the only parameters that could soak up the residual. The
gate stayed green throughout. Calibration fixes coefficients; it cannot fix a missing
mechanism, and a pre-registered prediction is how a missing mechanism shows itself.

---

## P1 — Jetson AGX Orin, one forward pass, Wan2.1-T2V-1.3B

**Registered:** 2026-08-03, before any Jetson measurement exists.
**Model state:** `rpu/` at this commit; coefficients fitted to the four RTX PRO 6000
anchors only. No Jetson data has ever touched the fit.

### Workload

| | |
|---|---|
| Model | Wan2.1-T2V-1.3B (d=1536, 30 layers, 12 heads, FFN 8960) |
| Unit | **one forward pass**, single branch, all 30 layers |
| Tokens | 1,560 new, 9,360 context |
| Arithmetic | 6.518 × 10¹² FLOPs |
| Modelled DRAM traffic | 5.607 GB |

### Prediction

| Quantity | Predicted |
|---|---|
| Compute-bound time | 59.1 ms |
| Memory-bound time | 27.4 ms |
| **Latency (the binding bound)** | **59.1 ms** |
| **Energy per forward pass** | **2.68 J** |

Coefficients used, all fitted to the RTX anchors: `compute_util` 0.8048, `bw_util` 1.0000,
`e_flop_fp4_pj` 0.3565, `e_byte_hbm_pj` 64.0.

### Stated assumptions, so a miss can be attributed

- Orin AGX 64 GB at its 60 W mode: 137 TOPS dense INT8 and 204.8 GB/s LPDDR5 [X,
  published specs, SKU not yet confirmed against the board].
- The workload runs INT8, matching the peak quoted above.
- `compute_util` and the energy coefficients transfer from a Blackwell workstation GPU to
  an Ampere-class embedded SoC. **This is the assumption most likely to be wrong**, and
  it is the main thing the measurement tests.
- `bw_util = 1.0` is not a belief; it is a coefficient resting on its bound because the
  anchors cannot identify it. If the measured latency is memory-bound and slower than
  predicted, this is the first suspect.
- No thermal throttling, no kernel-launch overhead, no framework overhead. The model has
  no term for any of them, so a systematic underestimate is the expected failure mode.

### What each outcome would mean

| Result | Reading |
|---|---|
| Within ~15 % | The coefficients transfer across architectures better than we had any right to expect. |
| Model too fast by 1.5–3× | The missing mechanisms (launch overhead, occupancy, throttling) are real and material. Expected. |
| Model too fast by >3× | A structural error, not a coefficient error. Stop and find it before fitting anything. |
| Model too slow | Almost certainly the peak or the precision assumption is wrong; check the SKU and what actually ran. |

### Result

*Not yet measured. To be appended after Phase 1.2, without editing anything above.*
