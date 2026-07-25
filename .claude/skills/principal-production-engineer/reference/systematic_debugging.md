# Systematic Debugging: Fast Root-Cause over Guess-and-Check

Covers a principled, repeatable debugging procedure; load when chasing any nontrivial bug, regression, flake, heisenbug, or prod-only failure instead of poking at the code.

## Doctrine

Reproduce -> isolate -> understand -> fix -> prevent. In order, no skipping.

- No fix without a reliable failing repro first. A bug you cannot trigger on demand is a bug you cannot prove fixed.
- Fix the root cause, not the symptom.
- Change ONE thing at a time. Predict the outcome before you run.
- Read the ACTUAL error/stack/logs before theorizing.
- Every fix ships with a regression test that fails on the old code.

## When to use / avoid

| Use | Avoid |
| --- | --- |
| Intermittent, regression, or prod-only failures | One-line typo with an obvious, type-checked fix |
| You have already guessed twice and missed | A failure the compiler/linter already pinpoints |
| Concurrency, memory, or performance bugs | Trivial config edits with instant feedback |
| "Works on my machine" / flaky CI | — |

## The procedure

1. **Reliable repro.** Make the failure deterministic. Pin and capture every input that matters: arguments, fixtures, env vars, config, RNG seed, clock, locale, timezone, container image, dependency lockfile. Script it into a single command so anyone can rerun it. If it only fails 1-in-N, wrap it in a loop until it fails every time or you understand the nondeterminism.
2. **Minimize.** Shrink to the smallest input and smallest code path that still fails. Delete unrelated config, stub dependencies, trim the dataset. A smaller repro narrows the search space and often names the cause by itself. Use a minimizer (`creduce`/`cvise` for C/C++, `shrinkray`, or a property-test shrinker) when manual trimming stalls.
3. **Bisect — in time and in space.**
   - *Time:* binary-search the introducing commit.
     ```sh
     git bisect start <bad> <good>
     git bisect run ./repro.sh   # exit 0 = good, 1-124 (not 125) = bad
     git bisect reset
     ```
   - *Space:* binary-search the failure across modules — disable half, see which half keeps failing, recurse.
4. **One hypothesis, one test.** State a single falsifiable hypothesis ("the cache returns a stale entry after eviction"). Predict what you'll observe if it's true. Change exactly one variable and check the prediction. Wrong prediction is information — log it and form the next hypothesis.
5. **Read the evidence.** Read the full stack trace, the actual exception type and message, the surrounding log lines, and the values involved. Do not skim to the first familiar word. The bug is usually stated plainly somewhere you didn't look.
6. **Instrument.** Add visibility, don't guess:
   - drop into a stepping debugger at the failing frame;
   - add structured logs at decision points (remove them later);
   - record/replay for nondeterministic bugs;
   - assert invariants so the program stops at the first wrong state, not the downstream crash.
7. **Fix the root cause; add a regression test.** Write a test that reproduces the bug and fails on the unfixed code, then apply the minimal fix at the cause. Run the test against the old code to confirm it goes red, then against the fix to confirm green. See the `test-driven-verification` skill for deriving and gating that test.
8. **Clean up and confirm green.** Remove debug logging, temporary prints, commented-out code, and loosened timeouts. Rerun the full suite plus the new regression test.

## Tools by category

| Category | Tools |
| --- | --- |
| Stepping debuggers | `pdb`/`ipdb`, `gdb`, `lldb`, `dlv` (Go/delve), `node --inspect` / `--inspect-brk`, `jdb`/IDE for JVM |
| Record / replay | `rr record` + `rr replay` (deterministic reverse debugging) |
| Bisection | `git bisect run`; binary search by module/feature flag |
| Memory / thread / UB | ASan, TSan, UBSan, MSan; Valgrind (`memcheck`, `helgrind`); Go `-race`; `-fsanitize=...` |
| Syscalls / I/O | `strace -f`, `ltrace`, `dtruss`/`dtrace` (macOS), `bpftrace` |
| Profilers | `perf record/report`, `py-spy`, `pprof`, async-profiler, `flamegraph` |
| Prod-only bugs | structured logs, distributed tracing (OpenTelemetry), metrics, exemplars, request IDs |
| Crashes / hangs | `python -X faulthandler` / `faulthandler.dump_traceback`, core dumps + `gdb`/`lldb`, `py-spy dump` on a live PID |

## Special cases

- **Heisenbugs / races:** run under TSan or `rr`; stress with a tight loop and high concurrency; pin schedulers/affinity to expose ordering. The race is real even if logging hides it.
- **Flaky / order-dependent tests:** randomize test order and seeds (`pytest -p randomly`, `--shuffle`); run the single test in isolation vs. in suite to find shared-state leakage.
- **Works locally, fails in prod:** diff the environment, not the code — data, scale, config, dependency versions, clock, permissions. Reach for observability (traces/logs/metrics) before trying to reproduce locally.
- **Performance regressions:** profile first to find the hot path, then `git bisect run` a benchmark with a pass/fail threshold to find the introducing commit.

## Prefer / avoid

| Prefer | Avoid |
| --- | --- |
| Reliable repro before any code change | Fixing blind because you "know" the cause |
| One change, predicted, then verified | Changing several things and rerunning |
| Reading the full stack/log | Print-and-pray with no hypothesis |
| Fixing at the root cause | Swallowing the exception or adding a retry to mask it |
| Asserting invariants to fail early | Debugging downstream of the first corruption |
| Deleting debug cruft before merge | Leaving `print`, commented code, loosened timeouts |

### Anti-patterns

- **Shotgun debugging:** random edits until the symptom disappears — you've hidden the bug, not fixed it.
- **Symptom fix:** `try/except: pass`, a blanket retry, a sleep, or a bumped timeout over a real defect (see [failure_policy.md](failure_policy.md) on silent fallback).
- **No-repro fix:** you cannot prove it was the cause or that it's gone.
- **Multi-variable change:** when it passes, you don't know which change mattered.

## Bugfix review checklist

- [ ] Is there a regression test that **fails on the old code** and passes on the fix?
- [ ] Is the root cause stated explicitly (not just "fixed the crash")?
- [ ] Is the fix minimal and located **at the cause**, not a downstream patch?
- [ ] Is the failure handled per [failure_policy.md](failure_policy.md) — no new silent fallback or masking retry?
- [ ] Was all instrumentation (debug logs, prints, commented code, loosened timeouts) removed?
- [ ] Did the full suite + new test run green?

## Verification

| Command | What it tells you |
| --- | --- |
| `git bisect start <bad> <good>` + `git bisect run ./repro.sh` | The exact commit that introduced the failure (repro must exit 0=good, 1-124=bad, 125=skip). |
| `rr record ./repro && rr replay` | Deterministic re-execution; step backward (`reverse-continue`) to the first wrong state. |
| `clang++/gcc -fsanitize=address,undefined` then run | ASan: out-of-bounds, use-after-free, leaks. UBSan: signed overflow, bad shifts, misaligned access — with file:line. |
| `-fsanitize=thread` / `go test -race` | Data races: the two stacks and the unsynchronized address. |
| `valgrind --tool=memcheck` | Uninitialized reads, invalid frees, leak summary (slower, no rebuild needed). |
| `strace -f -e trace=... ./repro` | Real syscalls and errnos across threads/children — which open/connect/read actually failed and why. |
| `py-spy dump --pid <pid>` / `python -X faulthandler` | Stacks of every thread in a live or hung process — no instrumentation, no restart. |
| `perf record ./bench && perf report` | The hot path consuming the regression's time. |

Confirm the fix by rerunning the **minimized repro** and the **new regression test** against both old and new code: red then green. See [agent_workflows.md](agent_workflows.md) for running this loop autonomously.
