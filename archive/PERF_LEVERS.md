# PERF_LEVERS.md — workload-shaping ledger, v2 (post-scrutiny)

Companion to [`CHIP_SPEC.md`](CHIP_SPEC.md). The chip is **energy-rate-limited** (spec §2),
so every lever is scored by its reduction of **chunk energy** — that *is* speed at head
power. Tags: **[M]** measured here, **[S]** our instrument, **[X]** external literature,
**[T]** estimate/bet. **v2 is the adversarial-scrutiny pass**: each lever carries a verdict;
v1's numbers are corrected where they didn't survive.

Ledger A (architecture η, required 2.15 solid at 40 W parity [S], evidence 1.6–3.2× [X]) and Ledger C (sub-Vmin,
spec §6b) are unchanged. This file is Ledger B: levers that shrink the *work*.

## The v2 verdict table

| # | Lever | Verdict | v1 → v2 estimate (chunk-energy ×) | What scrutiny found |
|---|---|---|---|---|
| B1 | Diffusion feature caching across steps | **REFUTED for our schedule** | 1.3–1.7 → **1.0–1.2, Quality mode only; 1.0 in Deadline mode** | TeaCache-class gains are measured on 50-step schedules; the serving literature states directly that intra-request caching is **"ineffective on industrial 4-step distilled models"** [X, arXiv:2604.04451]. Our 3-step schedule is past that cliff; 1-step has nothing to cache across. Remnant: CFG-pair feature reuse (FasterCache-style) in Quality mode only. |
| B2 | Sparse video attention (sliding-tile class) | **SURVIVES, trimmed** | 1.3–1.6 → **1.15–1.45** | STA's 10×-attention/3×-e2e is real [X, arXiv:2502.04507] but measured on ~100k-token generation with aesthetic metrics. Our window is only 18.7k tokens (less shrinkable) and the quality bar is *physical consistency for control*, unvalidated [T]. Tile-native mapping to our fabric stands (static masks in the sequencer; GPU STA gets 59% MFU, etched tiles should exceed 90%). |
| B3 | 2:4 structured weight sparsity | **SURVIVES, conditioned** | 1.2–1.4 → **1.2–1.35, requires sparse fine-tuning** | Hardware evidence solid (30–36% perf/W measured [X]). Two honest costs v1 skipped: sparsity metadata adds 2 b per 4 elements → weight stream shrinks to 0.56× not 0.50×; and control-policy accuracy under 2:4 is unmeasured — the model team must fine-tune sparse, not one-shot prune. |
| B4 | Token merging / N_new reduction | **SURVIVES, cautious** | 1.15–1.35 → **1.1–1.3** | ToMe numbers are image-generation; our tokens are already 8×8×4 VAE-compressed, and merge/unmerge error compounds across diffusion steps. Overlaps B2 (both prune attention work) — priced in composition, kept as an independent knob because it also cuts GEMM work. |
| B5 | KV cache FP8→FP4 | **SURVIVES** | **1.03–1.06** | 4-bit KV ≈ lossless is well-replicated in LLMs [X: KIVI lineage]; video-DiT KV quantization exists (QuantCache). Small energy but −26% stream time and half the KV-buffer SRAM. 2-bit (KIVI/LogQuant) stays on the worth-trying list, not the ledger. |
| B6 | FLASH-D / static-max softmax | **SURVIVES, minor** | 1.02–1.05 → **1.01–1.03** | The −20% power is on the attention *unit*, which is ~3% of our die budget — v1 over-credited it. The static-max idea (fixed FP8 scales ⇒ per-layer precomputed max bound, delete the online-max recurrence) survives as our own [T] and is nearly free to try at gate 1. |
| B7 | **Cross-chunk reuse (receding-horizon overlap)** | **UPGRADED — now the flagship** | 1.0–1.5 [T] → **1.3–2.0 (Quality) / 1.0–1.45 certified (Deadline) [X/T]** | v1 called it the most speculative; scrutiny found it's the *best*-anchored: **WorldCache: 2.3× at 99.4% baseline quality on Cosmos-Predict2.5-2B** — an actual video world model [X, arXiv:2603.22286]; **Chorus: 1.45× on 4-step distilled models via inter-request reuse** [X, arXiv:2604.04451] — the same mechanism class, proven exactly where B1 dies. This is also the lever *only* a world-model chip has reason to etch. |

## The B7 determinism resolution (new, important)

Content-aware caching is dynamic — naively it breaks the static-schedule proof. Resolution,
two-tier:
- **Quality mode:** dynamic reuse allowed freely (no hard deadline) — full WorldCache-class
  gains; decisions in the update-engine µcode; features live in the existing DRAM ring.
- **Deadline mode:** the schedule **reserves the worst-case (no-reuse) slot**; dynamic skips
  save *energy and average latency*, never claimed against the worst case — miss-rate proof
  intact. A skip can only count toward the deadline if the reuse floor is **structurally
  guaranteed** — and the founder's train-time real-time chunking is exactly the tool that
  can *train the overlap in* [F], turning a heuristic into a certifiable floor. This
  model-side guarantee is the single highest-value co-design experiment on the list.

## Composition — per mode (v1 composed one number for both modes; that was wrong)

~30% log-space overlap discount applied (all levers harvest world-state smoothness):

| Mode | Live levers | Naive product | **Discounted estimate** |
|---|---|---|---|
| **Quality** (3-step CFG) | B1r·B2·B3·B4·B5·B6·B7 | 2.1× → 6.7× | **≈ 1.7× → 3.8×** |
| **Deadline** (1-step distilled) | B2·B3·B4·B5·B6·B7-certified | 1.6× → 4.0× | **≈ 1.4× → 2.6×** |

## What the stack buys — corrected goals table

| Goal | Status after v2 scrutiny |
|---|---|
| **Relative 2× vs Thor** | unchanged — rides on η ≥ 2.15 solid (Ledger A, 40 W parity). Etch realization edge on B2/B3 (~1.2–1.4× relative [T]) is upside, not headline. |
| **Absolute 5 Hz Deadline Mode** | **v1's "160–250 ms at η=2.79" was WRONG** — it applied B1 and the full stack to a mode where B1 is inapplicable. Corrected (40 W parity): 540 ms ÷ (1.4–2.6) ≈ **208–386 ms at η = 2.15**. 5 Hz closes with **η ≈ 3 AND mid-stack Ledger B** (~185 ms), or a certified-floor B7 at the high end, or further model compression. Honest status: *plausible, not yet on the boundary.* |
| Quality-mode replan | 6.2 s → **≈ 1.6–3.6 s** at η = 2.15 — approaching 0.5 Hz full-quality replanning. |

## Grand total (v2)

| Stack | Multiplier | Status |
|---|---|---|
| Ledger A: architecture η | 2.15 solid / 3.0 target; 1.6–3.2 evidenced | the priced bet [S/X] |
| Ledger B: workload shaping | **1.4–2.6× (Deadline) / 1.7–3.8× (Quality)** | scrutinized, task-gated [X/T] |
| Ledger C: sub-Vmin LVI | 1.5–2.5× | gated side bet [T] |
| **Total vs naive Blackwell execution** | **≈ 4–10× (A×B, mode-dependent; mid ≈ 7×)**, up to ~25× with C | v1 said 7–10×; v2 honesty widens the band downward |

## Worth trying, not yet counted (kept deliberately)

- **B7-dynamic in Deadline mode with a trained reuse floor** — the co-design experiment;
  if train-time chunking certifies ≥30% reuse, Deadline-mode 5 Hz at η ≈ 3 becomes real.
- **Static-max softmax** (ours) — near-free to evaluate at gate 1.
- **2-bit KV** (LogQuant-class) — another ~1.03× and −13% stream if control quality holds.
- **V:N:M sparsity beyond 2:4** [X: up to 2× e2e] — bigger than B3 if the policy tolerates it.
- **Inter-chunk latent warping** (WorldCache's motion-adaptive blending) — pairs with B7;
  could push Quality-mode reuse past 2×.
- **Heterogeneous step allocation** (fewer steps for background tokens [X, arXiv:2605.06892])
  — a B1 substitute that *does* work at few steps by making step count spatially adaptive.

## Non-energy levers (excluded from multipliers, load-bearing anyway)

**Scheduled refresh (spec §4)** — ~0× energy; avoids the 7% nominal / **14–28% hot-head**
opportunistic-refresh bandwidth tax and zeroes refresh jitter by construction (miss-rate
proof prerequisite). Interaction: Ledger B shrinks compute faster than the stream, so the
conveyor approaches binding exactly as these levers mature — scheduling refresh is what
keeps Ledger B's gains from being clawed back. [X: JEDEC + automotive LPDDR5 practice; S/T]

## Verification hooks (all pre-silicon)

1. Every surviving lever is Tier-1-simulable as a `WorkloadParams` sweep — no core edits.
2. B2/B4/B7 quality costs measurable on the local RTX proxy with task metrics.
3. Gate-1 addendum: µcode/sequencer budget for static masks, merge permutations, reuse
   thresholds (≪1% die [T]); B7's worst-case-slot scheduling folds into the existing
   deadline analysis.
