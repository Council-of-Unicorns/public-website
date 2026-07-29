# FM-RPU Tier-1 feasibility (measured RTX PRO 6000 calibration)

## Calibration status

- Gate: **PASSED**
- Tolerance: 15% relative error on latency AND energy
- Anchors within tolerance: 4 / 7

## Per-anchor reproduction error

| Anchor | Latency rel. err | Energy rel. err | Within tol |
| --- | --- | --- | --- |
| b200_dreamzero_3step | 40.2% | 61.7% | no |
| dreamzero_public_16step | 40.3% | 61.9% | no |
| thor_point | 39.5% | 65.0% | no |
| rtx_pro_6000_1step_batch1_n3120 | 2.7% | 0.2% | yes |
| rtx_pro_6000_2step_cfg_n3120 | 0.9% | 0.5% | yes |
| rtx_pro_6000_3step_cfg_n1560 | 4.6% | 2.4% | yes |
| rtx_pro_6000_3step_cfg_n3120 | 0.7% | 1.5% | yes |

## FM-RPU feasibility (region with confidence bands)

- Feasibility region: p_feasible=0.0%; latency quantiles [p50=284.38 ms, p90=423.99 ms, p99=528.18 ms]; 90% CI on deadline margin [-248.87, +25.00] ms (n=256)

## Sensitivity ranking

| Rank | Input | Influence (std of binding feasibility margin) |
| --- | --- | --- |
| 1 | bw_util | 6.9733 |
| 2 | n_new | 5.5753 |
| 3 | step_compression | 1.1911 |
| 4 | e_byte_hbm_pj | 0.3697 |

## Thor bandwidth wall

- Crossover BW (below it the deadline is missed): 350.0 GB/s
- Thor HBM BW: 273.0 GB/s — on the MISS side (Thor misses the deadline)

## A-vs-B gap (cost of generality)

- A perf/watt: 0.002835; B perf/watt: 0.002782
- Gap fraction (B's cost of generality): +1.9% (90% CI [-91.0%, +94.7%])
- A region: p_feasible=0.0%; latency quantiles [p50=277.87 ms, p90=386.01 ms, p99=525.26 ms]; 90% CI on deadline margin [-223.94, +30.42] ms (n=96)
- B region: p_feasible=0.0%; latency quantiles [p50=278.29 ms, p90=408.62 ms, p99=527.67 ms]; 90% CI on deadline margin [-223.83, +38.36] ms (n=96)

