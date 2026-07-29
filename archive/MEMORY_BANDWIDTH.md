# MEMORY_BANDWIDTH.md — the memory wall, taken seriously

Prompted by a real objection: WAN-class video models measure **memory-bandwidth-bound on
B200** [F], while our model calls the workload compute-bound. This doc reconciles that,
then lays out the full solution space — demand side, supply side, and re-provisioning —
each option with numbers and named parts. Tags: [M] measured here, [S] our instrument,
[F] founder-measured, [X] external, [T] estimate.

## 1. Reconciling "compute-bound on paper" with "memory-bound on B200"

Three stacked explanations, all load-bearing:

1. **Fusion is the whole ballgame — and GPUs don't guarantee it.** Our 14.8 GB/step
   assumes attention never materializes its score matrix. If it does (unfused or
   partially-fused kernels, fallback paths, exotic head patterns), the scores alone are
   `40 heads × 3,120 Q × 18,720 KV ≈ 2.3 GB/layer` — **~187 GB per forward, ~25× our
   entire stream** [S, arithmetic]. A GPU's memory-boundedness on WAN is at least partly
   *manufactured by imperfect fusion*; an etched pipeline makes the fused byte count a
   **guarantee by construction**. This is memory-bandwidth solution #1, and it costs nothing.
2. **Reuse-regime collapse at batch-1.** Our intensity (16,000 FLOP/B) assumes weights are
   reused across N_new×CFG ≈ 6,240 tokens. Real-time low-batch inference on a GPU realizes
   far less reuse (cache-thrashed 7 GB weight set, per-kernel re-reads). The workload has a
   **crossover** (design doc §A2 said so); B200-measured WAN sits on the memory side of it.
3. **Our instrument is blind here.** Every calibration anchor is a compute-bound matmul
   proxy; `bw_util` was never identified in the fit [S/D4]. All memory-regime numbers are
   [T] until a **real memory-bound B200/WAN anchor** (the founder's own profiling) is
   ingested — now a gate-1 item.

**Our candidate config sits near the ridge, not 50× clear of it** (4 PF / 307 GB/s →
ridge ≈ 10,900 vs intensity ≈ 16,200: only 1.5× compute-side margin, ~1.06× under hot-head
refresh derating [S]). The margin must be engineered, not assumed. Hence this ladder.

## 2. Demand side — cut the bytes (multiplies with everything below)

| Lever | Bytes effect | Evidence |
|---|---|---|
| **Fusion by construction** (scores never in DRAM) | removes a ~25× blowup *risk*; guarantees the 14.8 GB/step baseline | [S] arithmetic; the etched pipeline's defining property |
| F2 CFG sharing (already in design) | already counted (else 2× worse) | [S] |
| KV → FP4 (PERF_LEVERS B5) | KV 7.7 → 3.9 GB/step | [X] 4-bit KV ≈ lossless in LLM practice |
| Sliding-tile attention (B2) | KV *reads* ÷3–10 → 0.4–1.3 GB/step | [X] STA |
| 2:4 weights (B3) | weights 7.0 → 3.9 GB/step (incl. 2b/4elem metadata) | [X] |
| **Lossless entropy coding of the weight stream (new)** | further ×0.67–0.85 on weights: low-precision formats have concentrated exponent entropy; hardware decoders at one weight/clock are demonstrated; FP8-family streams compress to ~62–83% losslessly | [X: arXiv:2510.02676, arXiv:2502.00922, IEEE 9253521] — decoder sits in the dequant row, upstream of dequant |
| **Net demand after stack** | **14.8 → ≈ 4–6 GB/step** (~13–20 ms at 307 GB/s effective) | composition [T], each term task- or losslessly-gated |

## 3. Supply side — buy more bandwidth (the ladder, cheapest first)

| Option | Bandwidth | Cost/power | Status |
|---|---|---|---|
| **256-bit LPDDR5X (current spec)** | 307 GB/s | baseline | shipping |
| **Wider LPDDR5X: 384/512-bit** | 460 / 614 GB/s | linear PHY+balls; **Apple M4 Max ships 546 GB/s LPDDR5X on-package in a consumer laptop** — the existence proof at consumer cost | shipping [X] |
| **LPDDR6 (256-bit-class package)** | ~2.25× per package vs 5X → **0.7–1.0 TB/s at 512-bit-class**; **21% better energy/bit**; 24-bit channels with finer sub-channels (better concurrency for KV+weight dual streams) | LPDDR-class | JEDEC published; Samsung samples now, production 2026 [X] |
| **On-package memory (Apple-style)** | enables the wide buses above; shorter traces cut PHY pJ/bit and board area | package cost, not interposer cost | shipping practice [X] |
| **LPDDR6-PIM** | attention's KV·V and QKᵀ passes execute *inside the DRAM banks* — the KV stream stops crossing the interface entirely. LPDDR5-PIM sims: >2× perf, −60% energy on memory-bound tasks; SK hynix AiM (GDDR6-PIM) demonstrated **batch-1 LLM decode at 330 tok/s** — the memory-bound regime exactly | Samsung + SK hynix are **standardizing LPDDR6-PIM for on-device AI, release ~2026** [X] | emerging — our static schedule maps onto PIM constraints unusually well [T] |
| **3D hybrid-bonded DRAM-on-logic (gen-2 endgame)** | order-of-magnitude bandwidth *density* over HBM; **0.66–0.88 pJ/bit ≈ 77–83% below HBM** — kills the byte-energy term too; adopted in LLM accelerators 2025–26 | advanced packaging; thermal co-design (DRAM refresh vs logic heat — our scheduled-refresh machinery becomes *more* valuable) | [X: arXiv:2604.08044 + industry] |
| Single-stack HBM3E (explicit fallback) | ~0.8–1.2 TB/s | interposer $$, PHY power, height | only if everything above fails — the analysis that rejected it (spec §4) stands *unless* the memory-bound anchor forces it |

## 4. Re-provisioning — the ratio is the design variable

If the ingested B200/WAN anchor shows the true operating point is memory-heavier than our
model, the answer is not "add HBM" — it's **rebalance**: MAC area/power trades ~linearly
for PHY channels (e.g. 4 PF + 307 GB/s → 3 PF + 512-bit/614 GB/s inside the same envelope
[T]). A GPU cannot make this trade after the fact; we make it at gate 1 with the anchor in
hand. The chip's identity is *matched-to-the-ridge*, not *maximum-FLOPs*.

## 5. Bottom line

- Demand stack: **÷2.5–3.7** bytes. Supply ladder: **×1.5–3.3** within the LPDDR family
  alone (before PIM/3D). Combined margin over today's requirement: **~4–12×** — the memory
  wall is addressable **without HBM**, with named, shipping-or-2026 parts. [T composition]
- The two *structural* answers no GPU has: **fusion by construction** (the 25× blowup
  cannot happen) and **scheduled refresh** (no hot-head bandwidth tax) — both already in
  the spec.
- The one action that de-risks everything: **ingest the founder's memory-bound B200/WAN
  profiling as a calibration anchor** and re-run the crossover. Added to gate 1.

## 6. Founder constraint: prefer solutions WITHOUT aggressive quantization

Recorded design preference [F]: a safety-critical control policy should not depend on
aggressive quantization (INT2, FP4-KV, 2:4 pruning) to fit its memory system. Re-ranking
under that constraint:

- **Tier 1 (bit-exact, lead with these):** fusion-by-construction; lossless entropy coding
  of the weight stream (×0.62–0.83, exact); scheduled refresh; wider on-package LPDDR5X →
  LPDDR6 → PIM/3D; MACs↔channels re-provisioning. These alone carry the plan.
- **Tier 2 (structural approximation, task-gated, not quantization):** sliding-tile
  attention, cross-chunk reuse — change *which* work is done, not numeric precision.
- **Tier 3 (aggressive quantization — last resort only):** INT2 weights, FP4-KV, 2:4
  sparsity. 2-bit KV is dropped from the worth-trying list.

**Conservative-precision profile (no aggressive quantization anywhere):** FP8 weights
(14 GB) + native-FP8 KV (7.7 GB) ≈ 21.7 GB/step; lossless coding → ~15.5 GB/step.
At 307 GB/s: ~50 ms (tight under hot-head derating). At **512-bit LPDDR5X (614 GB/s):
~25 ms — comfortably inside the 73.7 ms compute shadow.** The supply ladder + lossless
coding buys the entire no-quantization position for package cost, not model quality.
Trade to state honestly: FP8-native compute raises FLOP energy ~1.7× vs FP4 (measured s
curve) — the conservative profile spends η headroom (or watts) to buy quality certainty.
Both profiles remain µcode-selectable; the dequant row's format flexibility (spec §6) is
what makes the choice reversible.

## Gate-1 additions (from this doc)

1. Ingest a real memory-bound B200/WAN anchor; identify `bw_util`; re-locate the workload's
   compute/bandwidth crossover [F→M].
2. Decide the provisioning ratio (MACs vs channels) against that anchor (§4).
3. Evaluate the lossless weight-stream decoder (§2) in the dequant-row Tier-2 model.
4. Track LPDDR6-PIM standardization; assess our schedule's PIM-mappability [T].
