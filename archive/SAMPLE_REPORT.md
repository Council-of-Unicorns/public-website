# FM-RPU Tier-1 feasibility (measured RTX PRO 6000 calibration)

## Calibration status

- Gate: **PASSED**
- Tolerance: 15% relative error on latency AND energy
- Anchors within tolerance: 4 / 7

## Per-anchor reproduction error

| Anchor | Latency rel. err | Energy rel. err | Within tol |
| --- | --- | --- | --- |
| b200_dreamzero_3step | 40.3% | 64.7% | no |
| dreamzero_public_16step | 40.4% | 64.9% | no |
| thor_point | 39.6% | 68.0% | no |
| rtx_pro_6000_1step_batch1_n3120 | 2.5% | 0.8% | yes |
| rtx_pro_6000_2step_cfg_n3120 | 0.7% | 1.1% | yes |
| rtx_pro_6000_3step_cfg_n1560 | 3.9% | 2.5% | yes |
| rtx_pro_6000_3step_cfg_n3120 | 0.5% | 2.1% | yes |

## FM-RPU feasibility (region with confidence bands)

- Feasibility region: p_feasible=0.0%; latency quantiles [p50=284.39 ms, p90=424.00 ms, p99=528.16 ms]; 90% CI on deadline margin [-248.82, +24.99] ms (n=256)

## Sensitivity ranking

| Rank | Input | Influence (std of binding feasibility margin) |
| --- | --- | --- |
| 1 | bw_util | 5.3008 |
| 2 | n_new | 4.3216 |
| 3 | step_compression | 0.9062 |
| 4 | e_byte_hbm_pj | 0.0887 |

## Thor bandwidth wall

- Crossover BW (below it the deadline is missed): 350.0 GB/s
- Thor HBM BW: 273.0 GB/s — on the MISS side (Thor misses the deadline)

## A-vs-B gap (cost of generality)

- A perf/watt: 0.002781; B perf/watt: 0.00273
- Gap fraction (B's cost of generality): +1.8% (90% CI [-91.0%, +94.7%])
- A region: p_feasible=0.0%; latency quantiles [p50=277.90 ms, p90=386.02 ms, p99=525.19 ms]; 90% CI on deadline margin [-224.02, +30.39] ms (n=96)
- B region: p_feasible=0.0%; latency quantiles [p50=278.28 ms, p90=408.66 ms, p99=527.73 ms]; 90% CI on deadline margin [-223.83, +38.34] ms (n=96)

