# Domain templates for auto-research

Pick the template whose metric matches yours. Each template specifies: the metric, the harness shape, the mutable surface, typical secondary constraints, the noise budget (improvement threshold below which a run does **not** count as an improvement), and traps specific to that domain.

The skill's main loop is unchanged across domains — only the setup and the noise budget differ.

---

## 1. ML training loss / val_bpb / perplexity

**Metric**: validation loss, bits-per-byte, or perplexity on a held-out set. Lower is better.

**Harness**: a fixed wall-clock training budget (e.g. 5 minutes), a fixed evaluation routine on a frozen validation set, a fixed tokenizer and dataset. Karpathy's repo is the canonical example.

**Mutable surface**: typically a single `train.py` containing model architecture, optimizer, hyperparameters, training loop, batch size, model size. Data loading and evaluation live in a separate frozen file.

**Secondary constraints**:
- Peak VRAM under the device limit (e.g. `peak_vram_mb` ≤ 48 GB on a single H100).
- No new package dependencies.
- Run must finish within the time budget (no checkpoints that don't get evaluated).

**Noise budget**: for a deterministic eval pass on a fixed val set, the noise floor is roughly the difference between two consecutive seeds of the same config. For a quick proxy: if you run the baseline twice and the val metric differs by Δ, require improvements > Δ. In Karpathy's setup the eval is deterministic enough that any improvement past the 4th decimal counts.

**Traps**:
- **Eval leakage**: an experiment that touches the data pipeline or tokenizer breaks comparability against earlier rows. Treat `prepare.py`-style files as frozen.
- **Optimizing the wrong thing**: a larger model that doesn't finish training within the budget gets a worse final-eval metric than a smaller one that does. The metric correctly punishes this — trust it.
- **Compile / startup time burning the budget**: separate `training_seconds` from `total_seconds` in the log. Only the training portion is the budget; startup is overhead.
- **VRAM blowups**: at fixed budget, larger models steal time from training. Often a smaller, faster-iterating model wins.

**Idea menu** (rough order of expected info per unit compute):
LR sweep, warmup schedule, weight decay, batch size, optimizer (AdamW → Lion / Shampoo / Muon), activation (GELU → SiLU / SwiGLU), normalization (LayerNorm → RMSNorm), positional encoding (absolute → RoPE → ALiBi), attention variant (MHA → MQA → GQA), FFN ratio, depth-vs-width tradeoff at fixed params, fused kernels, mixed precision (bf16 → fp8 where supported), gradient checkpointing on/off, data ordering, EMA on weights.

---

## 2. GPU utilization / MFU / kernel throughput

**Metric**: model FLOPs utilization (MFU %), or tokens/sec, or step time in ms. Direction depends — `mfu_percent` higher is better, `step_ms` lower is better. **Pick one and stick with it for the entire run.**

**Harness**: a fixed model config, fixed batch size and sequence length, fixed number of warmup + measurement steps. The harness prints MFU and step time; it does **not** train to convergence — this is a perf microbenchmark.

**Mutable surface**: kernels, fusion choices, memory layout, dtype, `torch.compile` flags, parallelism config (TP / SP / DP), CUDA graphs on/off, attention implementation (`flash_attn` variants, SDPA backends).

**Secondary constraints**:
- **Correctness gate**: the modified kernel must produce output within numerical tolerance of the baseline on a fixed input (e.g. max abs diff < 1e-3 for bf16). Without this, "fastest" trivially becomes "wrong".
- Peak VRAM under the device limit.
- No regression in numerical stability on a quick training-loss probe (optional but cheap).

**Noise budget**: GPU perf is noisier than loss. On a shared host, run-to-run can vary 2–5%. On a dedicated host with locked clocks, 0.5–1%. Run the baseline at least twice at setup time and write the measured spread into the run-tag notes. Require improvements > 2× that spread.

```bash
nvidia-smi --lock-gpu-clocks=<MHz>     # before the run; restore --reset-gpu-clocks after
```

**Traps**:
- **Warmup-not-included**: timing the first step buries the result in compile time. Always discard N warmup steps before measuring.
- **Caches and persistence**: `torch.compile` cache, cuDNN autotuner, NCCL warmup. Either warm them every run or invalidate them every run — be consistent.
- **Thermal throttling**: long runs heat the GPU. Either keep runs short (<60 s of measurement) or measure thermal state.
- **Numerical correctness drift**: a kernel that's 20% faster but produces NaNs once per 1000 steps will pass the harness and destroy a downstream training run. Correctness gate is non-optional.
- **`nvidia-smi` is a poor profiler**: it tells you utilization but not why. Use `ncu` (Nsight Compute) for kernel-level signals, `nsys` (Nsight Systems) for timeline.

**Idea menu**:
Kernel fusion (qkv proj, ffn act+mul), attention impl swap, autotune block sizes, switch dtype, layout change (BSHD ↔ SBHD), CUDA graphs, `torch.compile` mode (`reduce-overhead` / `max-autotune`), pipeline microbatch size, gradient accumulation pattern, FSDP shard size, activation checkpointing granularity.

---

## 3. Network / RPC latency

**Metric**: p99 request latency in ms, *or* p95, *or* p50 — pick one. (Optimizing the median often hurts the tail. Pick the one that actually matters to the product.)

**Harness**: a fixed load generator (`wrk2`, `vegeta`, `oha`, k6, or a hand-rolled one) firing a fixed RPS for a fixed duration against a fresh process. Latency reported as a percentile from the generator, not from the server's own histogram (the server's histogram doesn't include client-side queuing delays).

**Mutable surface**: handler code, parser, allocator choice, thread pool config, I/O strategy (sync ↔ async, blocking ↔ epoll/io_uring), serialization library, caching, batching, connection pooling.

**Secondary constraints**:
- **Throughput floor**: improvement in latency must not come at the cost of dropping below baseline RPS.
- **Correctness gate**: response bytes must match baseline on a fixed probe input set.
- **Error rate**: zero non-2xx (or whatever the protocol's success code is) across the measurement window.
- Peak RSS within a stated limit.

**Noise budget**: network perf is the noisiest of the three domains. Run-to-run p99 spread of 10–30% is normal on a shared host, 3–10% on an isolated one. Require improvements > 2× measured spread. Run each candidate at least twice; record both rows in the log (different commits will obviously differ; use `--reps 3` style in the description).

**Traps**:
- **Coordinated omission**: most ad-hoc load gens under-report tail latency. Use a generator that maintains constant RPS rather than constant in-flight (`wrk2 -R`, `vegeta -rate`). If you must use closed-loop, document it.
- **First-request warm-up**: JITs, connection pools, allocators all warm up. Discard the first N seconds of the measurement window or include a warmup phase before measurement.
- **Network jitter from outside**: VM noisy neighbor, shared NIC. Either pin to dedicated hardware or accept a larger noise budget.
- **Server-side histogram lies**: if the server's queue is full, requests don't appear in its histogram at all. Client-side measurement is ground truth.
- **GC / compaction stalls**: in JVM/Go/.NET stacks, a perfect-looking p50 can hide GC tail latency. Always look at p99 and p99.9.

**Idea menu**:
Replace allocator (jemalloc, mimalloc, tcmalloc), pool buffers and connections, batch syscalls (sendmmsg / recvmmsg, io_uring), reduce copies (zero-copy, splice, sendfile), drop a layer of indirection in the parser, precompute serialization, sharded locks → per-CPU data, tune kernel sockopts (`SO_REUSEPORT`, `TCP_NODELAY`, ring sizes), CPU pinning, disable transparent hugepages or enable them, swap JSON lib, swap RPC framework.

---

## 4. Throughput (req/s, tok/s)

**Metric**: sustained successful requests/sec (or tokens/sec) over a fixed measurement window, at a fixed tail-latency cap. Higher is better.

**Harness**: closed-loop load gen ramped to find max sustainable RPS that satisfies a *secondary* latency constraint (e.g. "max RPS where p99 < 50 ms"). Or fixed offered load measuring achieved goodput.

**Mutable surface**: same as latency, plus concurrency / parallelism choices.

**Secondary constraints**:
- **Latency cap**: this is the gate. Throughput numbers without a latency cap are not comparable.
- **Error rate ≤ baseline**.
- Peak RSS / VRAM under limit.

**Noise budget**: similar to latency. Multi-run.

**Traps**:
- **Pyrrhic throughput**: removing the latency cap turns "throughput" into "how many requests does the queue swallow before failing". Always cap.
- **Saturation curve, not a point**: the same change can raise max throughput while lowering it at low load. Be clear which point on the curve you're optimizing.

---

## 5. Memory footprint

**Metric**: peak resident memory during a fixed workload (RSS for processes, peak VRAM for GPUs). Lower is better.

**Harness**: a fixed workload that exercises the realistic peak (inference with longest sequence, training with the chosen batch size, the load test for steady-state).

**Mutable surface**: data structures, layouts, dtype, allocator, caching strategy, lazy vs eager construction, arena vs per-object allocation.

**Secondary constraints**:
- **Latency / throughput floor**: a 50% memory reduction that doubles latency is usually not a win — gate it.
- **Correctness gate**.

**Noise budget**: peak memory is usually low-variance (≤ 1%) on isolated runs. Improvements > 1% count.

**Traps**:
- **Measuring the wrong peak**: RSS at the end of a run is not the peak. Use `/usr/bin/time -v` (Max resident set size), `getrusage`, or sample `RssPeak` from `/proc/<pid>/status`. For VRAM, `torch.cuda.max_memory_allocated()` or `nvidia-smi --query-gpu=memory.used --format=csv -l 1`.
- **Allocator caching**: an allocator that holds freed pages will report high RSS even when "logical" usage is low. Be consistent about what you're measuring.
- **Lazy work**: a "smaller" footprint that just defers allocations until later doesn't improve peak — it shifts it.

---

## 6. Compile / build time

**Metric**: clean build time in seconds (or full-cache cold build, depending on what's relevant). Lower is better.

**Harness**: a fixed `make clean && time make -j<N>` (or equivalent), on a fixed machine, with a fixed `-j`. The test suite must still pass — non-negotiable secondary constraint.

**Mutable surface**: include graph, template instantiations, PCH/modules config, build flags, code generation pragmas, source organization, dependency edges.

**Secondary constraints**:
- **All tests pass**.
- **Binary correctness** (output bytes / behavior unchanged for a probe input).
- Binary size within stated limit.

**Noise budget**: build time on warm disk caches has ~2–5% spread. Drop the OS page cache between runs or accept the spread.

**Traps**:
- **ccache / sccache** hiding the result. Either disable caches or wipe them between runs.
- **Parallelism noise**: `-j` interacts with other system load. Run on an otherwise idle machine.
- **Header changes that improve build time but break behavior**: a fast build of the wrong code is not a win. Test gate is non-optional.

---

## Picking a noise budget when you don't know one

Before the loop starts, run the baseline **three times in a row, unmodified**, and record the metric each time. Let σ be the standard deviation across runs. Use **2σ as the noise budget**: improvements smaller than 2σ from the best-so-far do not count as keeps.

This is mechanical and defensible. It also surfaces noisy harnesses early — if 2σ is larger than the gains you hope to achieve, the harness needs to be made less noisy *before* the loop starts. Fixing the harness is part of setup, not part of the loop.

---

## What every template has in common

1. **One number is the metric. Pick a direction.**
2. **A correctness gate** is almost always required as a secondary constraint. "Faster but wrong" is not a result.
3. **A noise budget**, measured at setup, not assumed.
4. **A frozen harness**. The moment you change it, the log resets.
5. **A single mutable surface**, named at setup.

If you can answer these five for your domain, you can run the loop.
