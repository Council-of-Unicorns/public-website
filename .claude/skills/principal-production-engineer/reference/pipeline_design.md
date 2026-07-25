# Software Pipeline Design

Decide whether to pipeline a multi-stage service, how to do it without pathology, and how to prove it helped. Load when the task involves stage decomposition, queues, workers, async handoffs, batching, or concurrent stages.

The running example throughout is a 3-stage service — `process input → compute candidates → optimize/select` — but the principles apply to any multi-stage system (ETL, request pipelines, ML inference, streaming).

## Doctrine

> A pipeline trades **locality** for **concurrency**. It is worth it only when concurrency clearly wins.

- Don't pipeline by default. Fuse first.
- A queue is a memory leak with a policy.
- The fastest intermediate object is the one never materialized.
- `throughput = min(stage_rates)` — pipelining doesn't speed up the slowest stage; it just lets others run ahead.
- Queues delay overload; they don't fix it. Clean rejection beats OOM.
- Modularity that destroys locality is not good engineering.

## Fused vs pipelined — what actually changes

| Property | Fused (synchronous) | Pipelined (queued) |
|---|---|---|
| Intermediate data lifetime | Microseconds, stack/register-hot | Until next stage drains the queue |
| Cache locality | Hot, often L1/L2 resident | Cold by the time consumer reads |
| GC promotion pressure | Low (young generation) | High (queue-resident → old gen) |
| Memory footprint | Bounded by one request | Bounded by queue capacities × item size |
| Backpressure | Implicit (caller blocks) | Must be explicit (or queues grow) |
| Debuggability | One stack trace | Distributed state across workers |
| Failure isolation | One failure kills one request | One slow stage can starve or flood others |

## When pipelining is appropriate

Pipeline only when at least one of these is clearly true:

1. **Different bottleneck resources per stage** — e.g., I/O → CPU → GPU. While one request waits on I/O, another uses CPU, another uses GPU.
2. **Stage latency varies and a bounded buffer smooths short spikes** — Stage 2 is usually 10 ms but occasionally 50 ms; a small queue keeps Stage 3 fed. Queues smooth *transient* variance, not sustained overload.
3. **The system is naturally streaming** — frames, tokens, audio chunks, log lines. The user benefits from partial progress.
4. **Different stages need different batch sizes** — Stage 1 handles requests singly; Stage 3 batches 64 at a time for GPU. Pipelining is the natural seam for batch reshaping.
5. **Operational isolation matters** — safety/fault containment, separate failure domains, separate scaling characteristics.

## When pipelining is usually wrong

- All stages CPU-bound and contending for the same cores and memory bandwidth.
- Whole request completes in microseconds-to-low-ms and is cache-local.
- Stage N+1 needs the full output of Stage N anyway (queueing just adds cold storage in between).
- Intermediate objects are large or allocation-heavy.
- One stage is always the bottleneck — pipelining only fills queues; it doesn't raise throughput.
- The justification is "microservices feel scalable" or "this looks cleaner."

A local function call with good locality regularly outperforms three services by orders of magnitude.

## The gate — design questions to answer before pipelining

If you cannot answer these, do not pipeline yet:

1. What bottleneck am I solving — and have I measured it?
2. Do stages use different resources, or will they contend?
3. What is the slowest stage? What is its rate?
4. Maximum memory held in each queue: `capacity × worst-case item size`?
5. Are all queues bounded?
6. What is the backpressure policy when queues fill?
7. What happens to in-flight work when Stage N+1 slows down or crashes?
8. Are intermediate objects compact and reusable?
9. Can Stage N+1 consume incrementally — so Stage N never materializes a pile?
10. Can Stage N and Stage N+1 be fused instead?
11. Can batching alone solve this without queues between threads?
12. What concrete metrics will prove the pipeline helped vs the fused baseline?
13. Does it improve p99, or only mean throughput? (These often diverge.)

## Standards

### Queues

Every queue is bounded. No exceptions.

```python
queue = Queue(maxsize=128)         # not Queue()
```
```go
ch := make(chan CandidateBatchHandle, 128)   // not make(chan T)
```
```cpp
BoundedSPSCQueue<CandidateBatchHandle, 1024> q;   // not std::queue<T>
```

Every queue must declare: **capacity**, **average item size**, **worst-case item size**, **ownership model**, **blocking / timeout behavior**, **drop or reject policy**, **metrics exposed**.

Estimate memory before adding a queue:

```text
queue_memory = capacity × avg_item_size

Example: 100 queued requests × 5000 candidates/req × 2 KB/candidate
       = 1 GB   — for one queue.
```

### Backpressure

Define overload behavior explicitly. Preferred order:

1. Bound the queue.
2. Block upstream briefly (small budget).
3. Reduce candidate / work budget for in-flight requests.
4. Drop low-priority work.
5. Reject the request cleanly with an overload status.
6. Never allow unbounded growth.

> "If the optimizer is slow, the queue will absorb it" — this is the failure mode, not the design.

### Intermediate representation

The most dangerous object is usually the intermediate (`CandidateSolution`, `ParsedEvent`, `EnrichedRecord`). Avoid queueing rich object graphs.

```cpp
// Bad — every candidate owns heap allocations
struct CandidateSolution {
  std::vector<float> features;
  std::vector<float> trajectory;
  std::string explanation;
  std::unordered_map<std::string, float> metadata;
  std::shared_ptr<ModelOutput> output;
};

// Better — parallel arrays in one batch
struct CandidateBatch {
  std::vector<float>   features;
  std::vector<float>   scores;
  std::vector<int32_t> parent_ids;
  std::vector<uint8_t> flags;
  size_t count;
};

// Best for hot pipelines — queue handles to pooled buffers
Queue<CandidateBatchHandle> q;   // not Queue<CandidateSolution>
```

For C++ data layout (SoA, generational handles, ECS, vectorization-friendly control flow), load `cpp-systems-internals` and read `reference/data_oriented_design.md`.

### Lifetime classification

| Class | Lives for | Allocation strategy |
|---|---|---|
| Request-local | One request | Stack, arena, short-lived heap |
| Stage-local | One worker, reused across requests | Pooled buffers |
| Queue-resident | Between stages | Compact, bounded, explicit ownership |
| Global | Process lifetime | Immutable or carefully synchronized |

**Goal:** keep large data request-local or stage-local. Avoid making large data queue-resident — that is where GC promotion, fragmentation, and cache misses originate.

### Ownership through queues

Be explicit about the handoff:

```text
Producer  owns while filling
Queue     owns while enqueued
Consumer  owns while processing
Pool      owns after release
```

Prefer move-only handles. Avoid `Queue<T*>` with ambiguous ownership and `Queue<shared_ptr<T>>` as ownership indecision.

### Fusion — the first alternative to try

```python
# Bad: materialize then optimize
candidates = list(generate_candidates(input))
best = optimize(candidates)

# Good: consume the stream
best = None
for c in generate_candidates(input):
    score = evaluate(c)
    if best is None or score > best.score:
        best = c
```

If Stage N+1 can consume incrementally, don't materialize a pile in between.

### Batching — the second alternative to try

Bounded by **both** size and time:

```text
max_batch_size = 64
max_batch_wait = 5 ms     # flush whichever fires first
```

Never let batch size grow because downstream is slow — that is unbounded queueing wearing a batch costume.

### Early pruning

Do not generate huge candidate sets and expect the optimizer to clean up.

```text
generate candidates in chunks
score cheaply / filter / threshold / keep top-k
optimize only survivors
```

Useful strategies: top-k, beam search, threshold pruning, successive halving, cheap approximate scoring, early stopping, streaming best-so-far.

If `candidates_optimized / candidates_generated` is tiny, the generator is too loose or the optimizer is doing rejection work.

## Language-specific failure modes

### Managed runtimes (Java, Go, C#, Kotlin, Scala, JavaScript, Python)

**Failure mode:** Objects sit in queues → survive young-gen GC → get promoted → major GC frequency rises → p99 spikes → throughput collapses.

**Prefer:** primitive arrays, compact records/structs, object pools, reused buffers, bounded channels, batch objects, arena-like allocation where the runtime supports it.

**Avoid:** per-element heap objects, deep object graphs, temporary maps and strings in hot paths, unbounded channels, long-lived queue items.

### C++ / Rust

**Failure modes:** allocator pressure, fragmentation, cache misses on cold queue-resident data, mutex contention, false sharing across producer/consumer cores, context switches.

**Prefer:** preallocated arenas, object pools, move-only batch handles, SPSC queues where possible, contiguous vectors, stable ownership, plain data in hot paths.

**Avoid:** `shared_ptr` per candidate, heap allocation per item, mutex-protected global queues, polymorphic candidates in hot paths, `unordered_map` and string-heavy metadata in hot paths.

For C++ ownership vocabulary, arena patterns, and sanitizer setup, load `cpp-systems-internals` and read `reference/cpp_ownership_and_arenas.md`.

## Required metrics — non-negotiable

Do not introduce a pipeline without instrumentation. Minimum set:

```text
request_end_to_end_ms              p50 / p95 / p99
stage_N_latency_ms                 p50 / p95 / p99   per stage
queue_N_depth                      gauge, sampled
queue_N_wait_ms                    histogram — time items sit waiting
candidates_generated_per_request
candidates_optimized_per_request
backpressure_events                counter
rejected_requests                  counter
rss_memory                         gauge
```

Add for managed runtimes:

```text
gc_pause_ms                        p50 / p99
major_gc_count                     rate
heap_live_bytes
promotion_rate                     bytes/sec to old gen
```

Add for C++ / Rust:

```text
allocation_count                   per request
allocated_bytes                    per request
cache_miss_rate                    perf-based
mutex_contention                   blocked time
```

**Most informative single graph: `queue_depth` over time.** If it trends upward, the system is unstable.

## Baseline comparison — the only way to justify a pipeline

Always build the synchronous version first. Then measure both:

| Metric | Fused baseline | Pipelined | Verdict |
|---|---|---|---|
| Throughput | | | |
| p50 / p95 / p99 latency | | | |
| RSS at steady state | | | |
| Allocation rate | | | |
| GC pause (managed) | | | |
| Cache misses (native) | | | |
| Queue depth / wait | n/a | | |
| Backpressure events | n/a | | |

**Accept the pipeline only when the tradeoff is clearly favorable.** Throughput +10% at the cost of p99 +300% and memory +400% is a regression dressed up as scale.

## Health signals

**Healthy pipeline:**
- Queue depths bounded and mostly low; return to near-zero between bursts.
- Queue wait time small.
- Workers mostly busy, not blocked.
- RSS reaches a stable plateau.
- GC pauses unchanged from baseline.
- Throughput meaningfully improved vs baseline.
- p99 within acceptable budget.

**Unhealthy pipeline:**
- Queue depth trends upward over time.
- Queue wait time grows.
- RSS grows with traffic and never recovers.
- Stage N+1 always saturated while Stage N runs ahead filling queues.
- Major GC count or pause time increases.
- Cache miss rate increases.
- p99 explodes (often while average looks fine).
- Backpressure fires constantly or rejections climb unexpectedly.
- Workers spend significant time blocked on output queues.

## Implementation order

1. Implement the simple **synchronous** version.
2. Measure per-stage latency and allocation.
3. Identify the actual bottleneck (not the assumed one).
4. **Improve data layout and reduce allocation first** — often this closes the gap without pipelining.
5. Add **early pruning** where work is being thrown away.
6. Add **batching** — within a stage, not across queues.
7. Add **bounded queues** only where concurrency clearly helps and stages use different resources.
8. Add **explicit backpressure** and overload policy.
9. Add **observability** before declaring success.
10. Split into separate **services or processes** only when operationally necessary (auth boundaries, deploy isolation, scaling axes, fault domains).

Do not skip directly to a distributed pipeline.

## Anti-patterns

1. **Microservice-first pipeline** — `InputService → CandidateService → OptimizerService` introduces serialization, network hops, versioning, deployment, and observability cost. One process first.
2. **Queue as shock absorber for sustained overload** — queues smooth spikes, not steady mismatch.
3. **Unbounded candidate generation** — fixing the optimizer's cost by giving it more inputs.
4. **Rich object graphs flowing through queues** — strings, maps, smart pointers, nested metadata per item.
5. **No defined overload behavior** — implicit policy is to OOM.
6. **"Pipelined because modular feels clean"** — modularity that destroys locality is not good engineering.
7. **Pipeline accepted on improved average throughput while p99 regressed** — measure p99, always.

## Code-review checklist

- Is every queue bounded? Is the bound chosen with item-size math?
- Is the worst-case queue memory documented and acceptable?
- Is backpressure policy stated explicitly (block / reduce / drop / reject)?
- Are intermediate items compact — primitive arrays or handles, not rich graphs?
- Is ownership across each queue unambiguous (move-only / pool / arena)?
- Is queue **wait time** instrumented, not just depth?
- Is p99 latency tracked, not just average / throughput?
- For managed runtimes: are queue items in young gen, or sitting long enough to promote?
- For native code: are producer/consumer queues per-thread (SPSC) or contended?
- Could Stage N and N+1 be fused? Why weren't they?
- Could batching alone solve the underlying motivation?
- Is there a fused baseline to compare against?
- Are stages independently measurable in the metrics?
- Does the slowest stage actually have headroom — or is the pipeline just filling queues?
- What happens to in-flight work when a worker crashes or a stage stalls?

## Verification commands

**Linux, general:**
```bash
perf stat -e cycles,instructions,cache-references,cache-misses,LLC-load-misses ./service
pidstat -r -p <pid> 1                # RSS over time
ps -o pid,rss,vsz,comm -p <pid>
```

**Go:**
```bash
go tool pprof http://localhost:6060/debug/pprof/heap
go tool pprof http://localhost:6060/debug/pprof/allocs
# In code: runtime.ReadMemStats for HeapAlloc, NumGC, PauseTotalNs
```

**Java:**
```bash
jcmd <pid> GC.heap_info
jcmd <pid> GC.class_histogram
# JVM flags: -Xlog:gc*:file=gc.log
# Profilers: JFR, async-profiler, VisualVM
```

**Python:**
```python
import tracemalloc, psutil, os
tracemalloc.start()
# ... workload ...
snapshot = tracemalloc.take_snapshot()
for stat in snapshot.statistics("lineno")[:10]:
    print(stat)
rss = psutil.Process(os.getpid()).memory_info().rss
```

**C++:**
```bash
heaptrack ./service
valgrind --tool=massif ./service
perf record -g ./service && perf report
# jemalloc:  MALLOC_CONF=prof:true,prof_prefix:jeprof
# tcmalloc:  HEAPPROFILE=/tmp/heap ./service
```

## The final gate

Introduce a pipelined architecture only when **all** of these are true:

1. Stages are independently measurable.
2. At least one stage would otherwise leave another resource idle.
3. All queues are bounded.
4. Backpressure is explicit.
5. Queue-resident data is compact and reusable.
6. Metrics exist for queue depth, queue wait, latency, memory, allocation, and overload.
7. A simpler fused or batched implementation has been considered first and rejected for a **measured** reason.

Pipeline when measurement shows concurrency beats locality. Not before.
