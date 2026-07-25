---
name: auto-research
description: Use when iteratively optimizing any measurable outcome overnight or unattended — training loss / val_bpb, GPU MFU and utilization, p50/p95/p99 latency, throughput (req/s, tok/s), memory footprint, binary or model size, compile time, energy per op. Enforces a fixed evaluation harness, a single mutable code surface, time-boxed runs on a dedicated branch, an append-only TSV results log, keep-on-improvement / git-reset-on-regression, a simplicity tiebreaker, and an autonomous never-stop loop. Companion to `principal-production-engineer` for measurement discipline and to `strategic-engineering-planner` for pre-loop scoping. Inspired by karpathy/autoresearch.
---

# Auto-Research

Iterate to a measurable target. Keep what works, throw out what doesn't, never stop until told to.

> Give the agent a small but real system with a fixed metric, and let it experiment autonomously.

This is a **workflow skill**: it defines an operating mode the agent enters explicitly. While the loop is running, the agent edits one code surface, runs one harness, logs to one file, and never asks "should I keep going?".

## When to use this skill

Use when **all** of these hold:

- There is **one number** that defines success (lower is better, higher is better — pick one).
- That number is produced by a **fixed evaluation harness** the agent will not modify.
- A single run completes in a **time the human is willing to wait per iteration** (Karpathy uses 5 min; for a CI flake-fixer it might be 90 s; for a kernel autotuner it might be 30 s).
- The work is exploratory: the agent will try many ideas, most will not work, and the human is fine paying for compute to find the ones that do.

Concrete fits:
- **ML training**: lower validation loss / val_bpb / perplexity under a fixed wall-clock budget.
- **GPU kernels / training step**: raise MFU, raise tokens/sec, lower step time, lower peak VRAM at fixed quality.
- **Networking / RPC**: lower p99 request latency, raise sustained throughput at fixed tail.
- **Compile / build**: lower clean-build time at fixed test-pass rate.
- **Inference**: lower tokens/sec/$ at fixed quality bar; lower TTFT.
- **Binary / model size**: smaller artifact at fixed accuracy or correctness gate.

Do **not** use when:
- The metric is subjective ("better code", "nicer API"), unenforced ("seems faster"), or human-judgement-bound. Define a harness first or load `strategic-engineering-planner` instead.
- The problem needs architectural exploration before optimization — load `strategic-engineering-planner` first to scope, *then* enter this loop.
- A single iteration is too expensive to run dozens of times (e.g. multi-day training, multi-hour deploys). Either shrink the proxy harness or use a different workflow.
- The system under test has hidden non-determinism large enough to swamp the metric — fix the harness first (see [reference/domain_templates.md](reference/domain_templates.md) on noise budgets).

## Core invariants — never violate

1. **The harness is read-only.** The eval code, the dataset, the load generator, the timing methodology — none of these change once the run starts. If you change them, the entire results log is invalidated.
2. **One mutable surface.** Name it explicitly at setup (e.g. `train.py`, `kernels/attention.cu`, `proxy/handler.rs`). All experiments edit only this surface. Do not drift.
3. **One branch.** All experiments live on `autoresearch/<tag>` (or whatever the agreed prefix is). The branch advances on improvement, resets on regression.
4. **Append-only log.** `results.tsv` grows monotonically. Never edit prior rows. Crashes get logged too.
5. **Time-boxed runs.** Every experiment has a fixed wall-clock budget. Exceeding it is a discard, not a "let it finish".
6. **Never-stop.** Once the loop has started, do not pause to ask the human if they want to continue. They might be asleep. Run until interrupted.

Violating any of these turns the results into noise. The whole point is that the metric across rows is comparable.

## Setup (do once, before the loop)

Work with the user to lock down five things. Do not skip this — a bad setup ruins every downstream iteration.

1. **The metric**. One number, direction (min/max), and how it's produced. Example: `val_bpb`, lower is better, printed by `train.py` after the eval pass.
2. **Secondary constraints**. Hard limits that disqualify a result regardless of the metric. Examples: peak VRAM ≤ 48 GB; p99 latency ≤ 50 ms; test suite must pass; no new dependencies.
3. **The mutable surface**. The single file (or small set) the agent is allowed to edit. Everything else is frozen.
4. **The time budget per run** and the **timeout** at which a run is killed (e.g. budget 5 min, kill at 10 min).
5. **The run tag**. Today's date or a short slug. Branch is `autoresearch/<tag>`. Branch must not exist yet.

Then:

```bash
git checkout -b autoresearch/<tag>     # from the agreed baseline commit
```

Initialize `results.tsv` with just the header (see format below). Do **not** commit `results.tsv` — leave it untracked. It's a local research artifact, not part of the codebase.

Run the baseline once, unmodified. Record it. From here, every comparison is against the best row in the log so far.

Confirm setup with the user. Then start the loop and do not stop.

## The loop

```text
LOOP FOREVER:
  1. Pick an idea.        — one specific, falsifiable change to the mutable surface
  2. Edit.                — minimal diff; do not refactor for its own sake
  3. git commit.          — short message starting with the idea ("try GELU"; "fuse k/v proj")
  4. Run the harness.     — pipe ALL output to a log file; do not stream into agent context
  5. Read the metric.     — grep one or two lines; never read the full log
  6. Decide.              — improved → keep (branch advances)
                          — worse or equal → git reset --hard HEAD~1
                          — crashed → discard, see Crashes below
                          — over timeout → kill, treat as crash
  7. Log to results.tsv.  — one row, append only
  8. Goto 1.
```

### Step 1 — picking ideas

Order ideas roughly by **expected information gained per unit of compute**, not by ambition. Early on, cheap changes that probe sensitivity (LR, batch size, one hyperparameter, one buffer size, one allocator choice) teach a lot. Later, combine near-misses, try architectural changes, read the references the code points to.

If you run out of ideas: re-read the in-scope files for angles you missed, look at the *near-miss* rows in the log (small regressions are often a clue), try combining two previous keeps, try a more radical change. Do not stop. Do not ask.

### Step 4 — running

Always redirect everything to a log file. Never let run output flood the agent context.

```bash
<run-command> > run.log 2>&1
```

`run.log` is overwritten each iteration — it is a scratch file, not history. History lives in git + `results.tsv`.

### Step 5 — reading the metric

Use a one-line extractor. Examples:

```bash
grep "^val_bpb:"        run.log     # ML loss
grep "^p99_ms:"         run.log     # latency
grep "^throughput_qps:" run.log     # throughput
grep "^mfu_percent:\|^peak_vram_mb:" run.log   # GPU
```

If the extractor returns empty, the run crashed or didn't reach the eval. `tail -n 50 run.log` to see the stack trace. Do not read the full log.

### Step 6 — the keep / discard rule

- **Improved** by at least the noise floor → keep the commit, branch advances.
- **Equal or worse** → `git reset --hard HEAD~1`. Branch returns to the previous best.
- **Tie with simpler code** → keep the simpler version. (See *Simplicity tiebreaker* below.)
- **Hits a secondary constraint** (OOM, latency cap, test fail) → discard, log as crash or constraint violation.

The "noise floor" is metric-dependent. For low-variance metrics (deterministic loss on a fixed eval) any improvement counts. For noisy metrics (latency, throughput on a shared host) require an improvement larger than your measured run-to-run spread. See [reference/domain_templates.md](reference/domain_templates.md) for per-domain noise budgets.

### Step 7 — the results log

`results.tsv` is tab-separated (commas appear in descriptions and break CSV). Header plus rows.

Recommended columns — keep the same set for the entire run:

```
commit	metric	secondary	status	description
```

- `commit` — short SHA (7 chars) of the experiment commit.
- `metric` — the primary metric. Six decimal places for loss-style metrics; one or two for latency/throughput. Use `0.000000` for crashes.
- `secondary` — the most important constraint number (peak VRAM in GB, p99 in ms, peak RSS in MB, etc.). Use `0.0` for crashes.
- `status` — `keep` | `discard` | `crash`.
- `description` — one short phrase. No commas. Past tense or imperative, e.g. `baseline`, `LR 4e-4 → 6e-4`, `swap GELU for SiLU`, `fuse qkv projection`.

Example:

```
commit	val_bpb	memory_gb	status	description
a1b2c3d	0.997900	44.0	keep	baseline
b2c3d4e	0.993200	44.2	keep	LR 4e-2
c3d4e5f	1.005000	44.0	discard	GELU activation
d4e5f6g	0.000000	0.0	crash	2x width (OOM)
```

For multi-metric studies (e.g. latency *and* throughput both matter), add columns but keep the primary metric in column 2. The decision rule in step 6 still uses only one number.

## Behavioral rules

- **Never stop** mid-loop to ask if the human wants to continue. They might be asleep. Run until interrupted.
- **Do not refactor** the mutable surface for cleanliness during an experiment. Refactoring while changing behavior makes the keep/discard signal meaningless. If a refactor is needed, do it as its own commit with no behavioral change, run the harness, and only keep it if the metric is unchanged.
- **Do not modify the harness** even if it "looks wrong". If the harness is genuinely broken, stop the loop, fix it, restart from a fresh baseline. Do not silently change it mid-run.
- **Do not install new dependencies** mid-run. They change the environment and invalidate prior rows. If a new dep is essential, treat it as a setup change: stop, install, re-baseline, start a new run tag.
- **Do not tee output** into the agent context. Always redirect, then grep.
- **Do not commit `results.tsv`**. It's local research output. If you want to share results, copy the file out.
- **Do not rewind the branch** to skip a streak of bad ideas unless you're truly stuck. The branch is supposed to advance; rewinding throws away earned progress. Use sparingly, if ever.

## Crashes and timeouts

- **Cheap to fix** (typo, missing import, off-by-one in the new code) → fix, recommit, re-run. Don't log a row until you have a real result.
- **Idea is fundamentally broken** (OOM at any batch size; an op doesn't exist on the target hardware) → discard, log as `crash` with a one-line description, reset, next idea.
- **Run exceeds the timeout** → kill the process, treat as crash, reset, next idea. Do not let runaway runs eat the rest of the night.
- **More than ~3 attempts to make a single idea work** → give up on that idea. Log as crash. Move on.

## Simplicity tiebreaker

When two outcomes are close on the metric, prefer the one with less code:

- Improvement that adds 20 lines of fragile code for a 0.001 gain → likely **discard**.
- Improvement of ~0 (within noise) that **deletes** code → **keep**. Simplification wins are real wins.
- Improvement that removes a dependency, a configuration knob, or a special case at no metric cost → **keep**.

Complexity has a half-life cost the metric doesn't capture. Bias toward small, comprehensible diffs.

## Reference index — progressive disclosure

Load only when relevant:

- [reference/domain_templates.md](reference/domain_templates.md) — per-domain setup recipes and noise budgets: ML loss, GPU MFU / kernel autotuning, network p99 latency, throughput, memory footprint, compile time. Pick the template that matches the metric and adapt.

## Routing

- **`strategic-engineering-planner`** — load *before* this loop if the problem still needs architectural exploration. The planner produces the scope and the harness shape; auto-research executes inside that scope.
- **`principal-production-engineer`** — load when designing the harness or interpreting a regression: measurement discipline, invariants, ownership of mutable state, what constitutes "honest verification". Especially relevant when the harness itself needs to be written from scratch.
- **`cpp-systems-internals`** — load when the mutable surface is C++ and an experiment touches cache lines, vectorization, allocation patterns, or codegen — i.e. when the metric is sensitive to mechanics this skill catalogues.

## Final response — when the human returns

After the loop has been interrupted, report:

- **Run tag and branch**.
- **Total iterations**: kept / discarded / crashed.
- **Baseline metric → best metric** (with secondary constraint values for both).
- **Top 3 keeps** by metric improvement, with one-line descriptions.
- **Surprises**: ideas you expected to work that didn't, ideas you didn't expect to work that did.
- **Dead ends** explored, so the human knows what's already been tried.
- **Next ideas** the agent would try if the loop resumed.

Do not editorialize. Cite the `results.tsv` rows.
