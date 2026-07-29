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

- Feasibility region: p_feasible=0.0%; latency quantiles [p50=1385.77 ms, p90=2074.08 ms, p99=2407.87 ms]; 90% CI on deadline margin [-2040.95, -574.31] ms (n=256)

## Sensitivity ranking

| Rank | Input | Influence (std of binding feasibility margin) |
| --- | --- | --- |
| 1 | step_compression | 1.0479 |
| 2 | n_new | 0.9497 |
| 3 | bw_util | 0.0214 |
| 4 | e_byte_hbm_pj | 0.0000 |

## Thor bandwidth wall

- Crossover BW (below it the deadline is missed): 350.0 GB/s
- Thor HBM BW: 273.0 GB/s — on the MISS side (Thor misses the deadline)

## A-vs-B gap (cost of generality)

- A perf/watt: 0.002797; B perf/watt: 0.002754
- Gap fraction (B's cost of generality): +1.6% (90% CI [-98.7%, +101.8%])
- A region: p_feasible=0.0%; latency quantiles [p50=1363.82 ms, p90=1816.24 ms, p99=2448.35 ms]; 90% CI on deadline margin [-1936.84, -625.37] ms (n=96)
- B region: p_feasible=0.0%; latency quantiles [p50=909.03 ms, p90=1314.68 ms, p99=1619.37 ms]; 90% CI on deadline margin [-1260.09, -312.25] ms (n=96)

