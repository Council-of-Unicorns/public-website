# Measurement & verification

The non-negotiable other half of DOD: an optimization is a hypothesis, and the
profiler is the only thing that confirms or kills it. Load this at the start of any
performance task (to find the bottleneck) and at the end (to prove the win). *A
"faster" claim without a measurement is folklore.*

## The protocol

1. **Baseline first.** Commit the obvious/scalar implementation and record its
   number on the real (or a faithful proxy) workload. Every later change is
   measured against this.
2. **Find the actual bottleneck before changing anything.** Profile. Classify the
   bind: **memory** (cache/TLB misses), **branch** (mispredicts), **front-end**
   (L1i / decode), **back-end/compute** (port pressure, dependency chains), or
   **I/O**. Optimizing a non-bottleneck is wasted complexity.
3. **Measure a noise budget.** Run the baseline 3+ times; take the run-to-run
   spread (≈2σ). An improvement smaller than the noise budget **does not count**.
   If the noise exceeds the gains you hope for, fix the harness before optimizing.
4. **One change at a time**, matched to the lowest unsatisfied rung of the
   optimization order. Re-measure against baseline. Keep iff it beats the noise
   budget **and** passes the correctness gate; otherwise revert. Tie → simpler code.
5. **Prove correctness alongside speed.** A faster kernel that is wrong (NaNs, a
   torn read, an off-by-one in the tail) is not a result. Gate every keep on a
   correctness check (exhaustive for small domains, randomized + oracle otherwise;
   ThreadSanitizer for concurrent state).
6. **Record the evidence.** What changed, before/after numbers, the exact command,
   and the bottleneck it addressed. If the fast path is conditionally compiled (ISA
   dispatch), keep the baseline as the documented oracle.

For driving a single number down/up over *many* unattended iterations on a frozen
harness, escalate to the `auto-research` skill — it formalizes this loop
(read-only harness, one mutable surface, append-only results log,
keep-on-improvement / revert-on-regression).

## Tools by question

| Question | Tool |
|---|---|
| Where is the time? | `perf record -g` + `perf report`; a sampling profiler / flame graph |
| Memory-bound? | `perf stat -e cache-misses,cache-references,L1-dcache-load-misses,LLC-load-misses` |
| TLB / paging? | `perf stat -e dTLB-load-misses,iTLB-load-misses,page-faults,major-faults` |
| False sharing? | `perf c2c record` + `perf c2c report` (HITM cache lines) |
| Branch-bound? | `perf stat -e branches,branch-misses`; `perf record -e branch-misses` |
| Front-end / L1i? | `perf stat -e L1-icache-load-misses,iTLB-load-misses,idq_uops_not_delivered.*` |
| What did the compiler emit? | `objdump -d -C`; Compiler Explorer (godbolt) |
| Did it vectorize? | `-Rpass=loop-vectorize -Rpass-missed=loop-vectorize` (clang); `-fopt-info-vec-all` (gcc) |
| Where's the binary bloat / symbol size? | `nm --print-size --size-sort \| c++filt`; `-ftime-report` for compile cost |
| Peak memory / allocations? | `valgrind --tool=massif`; `heaptrack`; `/usr/bin/time -v` (max RSS) |
| Symbol resolution / linkage? | `ldd`, `readelf -d`, `nm -D`, `LD_DEBUG=bindings` |
| GPU kernels? | `ncu` (Nsight Compute) for *why*, `nsys` for timeline — not `nvidia-smi` |

## Microbenchmark hygiene

- **Defeat dead-code elimination:** consume results (`benchmark::DoNotOptimize` /
  `ClobberMemory`, or write to a `volatile`/sink). An "infinitely fast" loop was
  optimized away.
- **Warm up, then measure:** discard the first iterations (cold cache, JIT/`torch.compile`,
  cuDNN autotune, branch-predictor training). Decide cache state deliberately —
  warm or flushed, consistently.
- **Measure the right percentile.** For latency, report p50/p95/p99/p99.9, not just
  the mean — tails are where GC pauses, page faults, and contention hide. For
  throughput, **gate on a latency cap** (uncapped throughput is "how much the queue
  swallows before failing").
- **Isolate the machine:** pin clocks (disable turbo/throttling) or keep runs short
  to avoid thermal drift; run on an otherwise-idle core; pin the thread. Lock GPU
  clocks for kernel benchmarks.
- **Type-pun and FP determinism:** when comparing a vector kernel to scalar, expect
  FP differences from FMA contraction/reassociation; pin them (route `a*b+c`
  through a no-FMA path) when you need bit-exact equivalence, or compare within a
  stated tolerance.
- **Redirect verbose output to a log; read the metric with a one-line extractor.**
  Don't stream full benchmark output into reasoning context.

## Reading the result honestly

- A win must clear the **noise budget**, not just be a smaller mean.
- **Tradeoffs are real:** "throughput +10%, p99 +300%, memory +400%" is a
  regression dressed as scale. State what got worse, not only what got better.
- **Trust the metric over intuition:** a model/kernel that's faster but produces
  wrong output must fail the gate regardless of its speed.
- **Simplicity tiebreaker:** within noise, keep the smaller/simpler diff;
  complexity has a cost the benchmark doesn't capture.

## Code-review checklist

- [ ] Is there a committed baseline and a stated target number?
- [ ] Was the bottleneck identified by a profile (not asserted)?
- [ ] Does each optimization cite a before/after measurement that beats the noise
      budget?
- [ ] Is there a correctness gate, and does the fast path pass it (bit-exact or
      within a stated tolerance; TSan-clean if concurrent)?
- [ ] Are tradeoffs (p99, memory, complexity) reported, not just the headline?
- [ ] Is a scalar/baseline path retained where the fast path is ISA-conditional?

## A minimal repeatable recipe

```bash
# 1. baseline number + noise budget
for i in 1 2 3; do ./bench --impl=baseline >> base.log; done   # inspect spread → 2σ
# 2. profile to find the bind
perf stat -e cycles,instructions,cache-misses,branch-misses ./bench --impl=baseline
perf record -g ./bench --impl=baseline && perf report
# 3. change one thing, re-measure vs baseline + correctness gate
./bench --impl=candidate --check && ./bench --impl=candidate >> cand.log
# 4. keep iff (candidate < baseline - 2σ) AND check passed; else revert
```
