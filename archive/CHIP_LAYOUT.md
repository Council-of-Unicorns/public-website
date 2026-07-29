# CHIP_LAYOUT.md — FM-RPU block-level system design (v0.1)

Companion to [`CHIP_SPEC.md`](CHIP_SPEC.md) (targets, modes, corrections ledger) and
[`CHIP_ROADMAP.md`](CHIP_ROADMAP.md) (phases and gates). Numbers marked **[I]** are
calibrated-instrument output (measured RTX PRO 6000 anchors, P6 green); numbers marked
**[E]** are first-order N4-class engineering estimates that Tier-2 (Accelergy-class tile
model) must confirm before RTL. Nothing here is tapeout-grade; this is the architecture
the phase gates evaluate.

## 0. Derivation of the headline sizes

- **MAC count:** 4 PF dense FP4 [I: the spec point that stays power-limited] at the
  wide-and-slow clock 1.05 GHz [E] → `4e15 / 2 / 1.05e9` ≈ **1.90 M MACs**.
- **Tile count:** 128×128 systolic tiles (16,384 MACs each; TPU-lineage geometry with
  128-fold input reuse) → 1.90M / 16,384 ≈ **116 → 120 tiles** (8 slices × 15).
- **Slice partition:** the frozen shapes divide exactly: d = 5120 = 8 × 640;
  ffn = 13,824 = 8 × 1,728 — no remainder-handling generality anywhere in the fabric.
- **SRAM spine:** sized by the residual stream, not weights (P3: no weight-sized SRAM
  can ever win): CFG-pair activations 2 × 3,120 × 5,120 B (FP8) = **32 MB**, +8 MB tile
  intermediates → 40 MB. Weight FIFOs 2 × 16 MB (tile-granularity ping-pong; step- or
  layer-granularity buffering is refuted in CHIP_SPEC §3). KV stream buffers 16 MB.
  Total ≈ **90 MB**.
- **Conveyor requirement:** stream one step's 14.8 GB [I: 7.0 GB FP4 weights + 7.7 GB
  FP8 KV] inside the 73.7 ms [I] step compute → ≥ 200 GB/s; provisioned 256-bit
  LPDDR5X @ 307.2 GB/s (1.5× margin). Capacity ≥ 16 GB [I: 7.0 + 7.7 + headroom].

## 0a. TPU-v1 lineage map (evidence transfer for every major block)

Our η evidence band is the TPU's, so the layout deliberately keeps a block-for-block
correspondence with the best-documented inference ASIC. Where we deviate, the deviation is
justified by a workload difference, not taste:

| FM-RPU block | TPUv1 ancestor | Same / deviation, and why |
|---|---|---|
| Weight FIFO A/B (2×16 MB) | Weight FIFO (4 tiles deep, double-buffered off DDR3) | same pattern; deeper tiles because our conveyor feeds 120 tiles not one array |
| Activation SRAM spine (40 MB) | Unified Buffer (24 MB) | same role (residual stream stays on-die); sized by our CFG-pair token count |
| FP32 accumulator SRAM per slice | 4 MB of 4,096×256 32-bit accumulators below the array | same pattern: narrow multiply, wide accumulate, dedicated SRAM |
| 128×128 systolic tiles | 256×256 MXU | smaller tiles: our shapes tile exactly at 128 (5120=40×128) and smaller tiles ease low-voltage droop containment (§6b of spec) |
| Conveyor DMA (counter prefetch) | host-pushed weights over PCIe | deviation: no host exists; the schedule is the DMA program |
| Online-softmax streamer | (none — TPUv1 had activation pipeline) | new; attention post-dates TPUv1. Art: FLASH-D / ExpMul (spec §6) |
| Schedule µcode ROM | CISC instruction stream from host | deviation: zero instructions in-band; the "program" is resident silicon |

## 1. Floorplan (~450 mm², N4-class [E])

```
┌─────────────────────────────────────────────────────────────────────┐
│  LPDDR5X PHY  ch0   │   ch1   │   ch2   │   ch3     (256-bit, 307 GB/s)
├─────────────────────────────────────────────────────────────────────┤
│  CONVEYOR DMA + ECC  →  WEIGHT FIFO A/B (2×16 MB)  →  DEQUANT ROW   │
│  (sequential prefetch, open-page, fixed trace)     (FP4→FP8, inline)│
├──────────────┬──────────────┬──────────────┬────────────┬──────────┤
│  SLICE 0     │  SLICE 1     │  SLICE 2     │  SLICE 3   │ KV       │
│  15× 128×128 │  15× 128×128 │  15× 128×128 │  15×128×128│ STREAM   │
│  PE tiles    │  PE tiles    │  PE tiles    │  PE tiles  │ BUFFERS  │
├──────────────┴───────┬──────┴──────────────┴────────────┤ (16 MB)  │
│   ACTIVATION SRAM SPINE (40 MB: residual stream,        │ + online │
│   2×(3120×5120) FP8 CFG pair, tile intermediates)       │ SOFTMAX  │
├──────────────┬──────────────┬──────────────┬────────────┤ UNIT     │
│  SLICE 4     │  SLICE 5     │  SLICE 6     │  SLICE 7   │ (flash-  │
│  15× 128×128 │  15× 128×128 │  15× 128×128 │  15×128×128│  attn    │
│  PE tiles    │  PE tiles    │  PE tiles    │  PE tiles  │  style)  │
├──────────┬───┴───────┬──────┴───────┬──────┴────┬───────┴──────────┤
│ SEQUENCER│ VECTOR    │ UPDATE       │ KV WRITE  │ SENSOR/ACTION IO │
│ µcode ROM│ UNIT      │ ENGINE       │ PATH      │ latent ingress · │
│ + chunk  │ (norms,   │ (µcoded      │ (ring     │ action egress ·  │
│ FSM +    │ adaLN,    │ flow-ODE /   │ append)   │ deterministic    │
│ watchdog │ GELU)     │ CEM, ~2%)    │           │ links, no PCIe   │
├──────────┴───────────┴──────────────┴───────────┴──────────────────┤
│  PMU + PLLs + always-on domain          DFT/JTAG        (south edge)│
└─────────────────────────────────────────────────────────────────────┘
```

## 2. Block budget

| Block | Contents | Area [E] | Power, Deadline mode [I/E] |
|---|---|---|---|
| MAC fabric (8 slices) | 120× 128×128 FP4 systolic tiles = 1.90 M MACs @ 1.05 GHz, low-V domain | ~55% (~250 mm²) | ~19 W |
| SRAM (~90 MB) | 2×16 MB weight FIFOs · 40 MB activation spine · 16 MB KV stream · misc | ~12% | ~2 W |
| Dequant row | FP4→FP8 inline, ~200 G elem/s, format-flexible (INT4/INT2 capable per spec §4) | ~2% | <1 W |
| Softmax/attention unit | online softmax (running max/sum) + transpose network; QKᵀ/AV run on the main fabric | ~3% | ~1 W |
| Vector unit | 8× 1024-lane FP8 SIMD: LayerNorm, adaLN, activations, residual adds | ~4% | ~1 W |
| Update engine | µcoded flow-ODE / CEM island (Part-B hedge; ~2% of datapath, priced [I]) | ~2% | <0.5 W |
| LPDDR PHY + DMA + ECC | 4×64-bit channels; sustained 74 GB/s in Deadline mode, bursts to 307 | ~8% | 1.5–4 W [I: e_byte range] |
| Sequencer + IO + PMU | schedule µcode ROM (1/2/3-step modes), watchdog, latent-in/action-out | ~4% | ~0.5 W |
| **Total** | | ~450 mm² | **~27–29 W** vs 30 W budget |

## 3. The three dataflows (what the etch fixes in copper)

1. **Weight conveyor:** DRAM → PHY → ECC → FIFO A/B ping-pong → dequant → column-broadcast
   into all 8 slices → consumed on arrival, never resident. Fan-out-of-2 to the CFG pair at
   slice input (F2 — fetched once, used twice [I]). The address trace is identical every
   chunk: the prefetcher is a counter, not a predictor.
2. **KV loop:** DRAM ring → KV stream buffers → fabric as B-operand of QKᵀ (scores) and AV
   (context), online-softmax unit between the two passes → the new chunk's K/V written back
   via ring-append → **ring-pointer shift at chunk end** (no copy). The 7.7 GB window is
   DRAM-resident by necessity (CHIP_SPEC §3 correction #1).
   *Refresh note:* the sequencer owns DRAM refresh — per-bank refresh commands are issued in
   the statically-known conveyor-idle windows (~35% of each step at 4 PF), making refresh
   interference zero by construction (CHIP_SPEC §4). The KV ring's bank rotation is aligned
   with the refresh rotation so a bank is never refreshed in its own read window.
3. **Token loop (on-die):** activation spine holds the CFG-pair residual stream (32 MB);
   per layer: spine → QKV → attention → out-proj → cross-attn → FFN (column-tiled so the
   86 MB FFN intermediate never materializes) → spine. Between diffusion steps:
   spine → update engine → spine. Data leaves the die only as 64 action tokens.

## 4. Domains

| Domain | Voltage/clock | Contents | Rationale |
|---|---|---|---|
| Fabric | ~0.55–0.65 V [E, gated on the DVFS measurement] @ 1.05 GHz | MAC slices, dequant | the wide-and-slow η lever — V² energy |
| Memory/NoC | nominal | SRAM spine, FIFOs, softmax, vector | timing margin for SRAM |
| PHY | per LPDDR5X spec | memory interface | — |
| Always-on | low-leakage | sequencer, watchdog, PMU | owns degraded-mode behavior on a missed chunk |

## 5. Design decisions embedded here (and their reversals)

- **Attention on the main fabric, not a dedicated engine.** Attention is 39% of chunk
  FLOPs [I]; a dedicated engine sized for it would nearly double array area. Chosen: two
  fabric passes with an online-softmax streamer between. *Reversal condition:* if Tier-2
  shows the softmax-streamer round-trip through the spine costs > ~5% of chunk energy,
  revisit a fused attention pipeline.
- **Column-partitioned slices** (over d/ffn), exact-divisor shapes only. *Reversal:* a
  model revision that breaks the divisors forces either pad-generality (energy) or respin.
- **Tile-granularity weight streaming** (never layer- or step-granularity buffering) —
  forced by SRAM arithmetic (CHIP_SPEC §3 correction #3).
- **Sequencer is a µcode ROM, not a hardwired FSM** — carries the three operating modes
  (CHIP_SPEC §5); schedule revisions without respin.

## 6. Open at this level (pre-Tier-2)

- Final fabric voltage point — nominal-Vmin baseline now; sub-Vmin is the gated §6b bet.
- ~~FP16 vs FP32 accumulate~~ **RESOLVED** (spec §6): FP32 accumulators in dedicated SRAM,
  TPUv1 lineage; FP16 stays as a task-checked fallback.
- **PE-level dataflow variant — the gate-1 Timeloop A/B** (weight- vs output-stationary vs
  broadcast/reduction-tree). Working hypotheses to test, from the SCALE-Sim v3 / Timeloop
  literature: WS is favored at our tile size and extreme weight reuse (6,240 uses/fetch);
  OS often wins once DRAM stalls are modeled — but our conveyor has *no* stalls by
  construction, which removes OS's usual advantage; attention (weight-free) may prefer a
  different stationary choice than the FFN, and nothing forbids **per-pass dataflow**
  (WS for GEMMs, OS for QKᵀ/AV) since the schedule is etched. Decision principle per
  §6a: maximize ops per operand fetched from any addressed structure; prefer wired shift
  paths over addressed reads (Hameed ISCA'10).
- Whether the vector unit folds into the slices vs stays centralized.
- Exact tile count vs clock retune once the measured V/f curve exists.
- Process node and die-area budget confirmation (the ~450 mm² figure is an estimate
  anchored on GPU tensor-core density ×2–3 for ASIC layout; Tier-2 owns this number).
