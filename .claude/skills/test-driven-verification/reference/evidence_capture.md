# Evidence Capture

Covers proving behavior a unit test can't fully assert — UI, end-to-end flows, cross-system integrations — by capturing a re-runnable artifact a reviewer trusts without redoing the work by hand. Load this when a change is visual, interactive, or spans processes/services, and a green unit suite alone won't convince a reviewer it works.

## Doctrine

> "Looks good on my machine" is not evidence. Evidence is an artifact a reviewer can regenerate with one command and inspect without trusting you.

- For anything **visual, interactive, or cross-system**, attach a hard artifact — screenshot, video, trace, HAR, or captured log.
- The artifact must be produced by a **repeatable command**, and that command travels with it. No command → not evidence.
- Prefer artifacts a reviewer can **re-run, not re-do**: they execute one line and see the same result, instead of clicking through a UI themselves.
- Unit/property tests still cover logic (see [test_design.md](test_design.md)); this file is for the boundaries they can't reach.

**Use evidence capture when:**

| Situation | Artifact |
|---|---|
| UI renders / layout / a visual regression | Screenshot (full page or element) |
| Multi-step user flow (login, checkout, wizard) | Playwright trace + video |
| Flaky timing / "works sometimes" interaction | Trace (timeline of every action + network) |
| Network contract with a 3rd party | HAR (recorded requests/responses) |
| CLI / TUI output, exit codes, prompts | `tmux capture-pane` snapshot |
| Whole stack working together | Ephemeral `docker compose` run log |

**Avoid / overkill when:** the behavior is pure logic with a deterministic return value — a unit test is cheaper, faster, and a better artifact. Don't screenshot what an assertion can prove.

## Browser flows with Playwright

Author by recording, then harden the generated code into assertions.

```bash
npx playwright codegen http://localhost:3000   # click the flow; it writes the test
npx playwright test                            # run; artifacts land in test-results/ + playwright-report/
npx playwright show-trace test-results/.../trace.zip   # open the timeline viewer
```

Configure capture in `playwright.config.ts` so artifacts appear automatically on failure (or always, while gathering evidence):

```ts
use: { trace: 'on', video: 'on', screenshot: 'only-on-failure' },
```

Short example — a checkout/login flow that captures a screenshot and (via config) a trace + video:

```ts
import { test, expect } from '@playwright/test';

test('user logs in and completes checkout', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill('demo@example.com');
  await page.getByLabel('Password').fill('correct horse');
  await page.getByRole('button', { name: 'Sign in' }).click();

  await page.getByRole('link', { name: 'Add to cart' }).first().click();
  await page.getByRole('button', { name: 'Checkout' }).click();
  await expect(page.getByText('Order confirmed')).toBeVisible();      // the assertion

  await page.screenshot({ path: 'evidence/checkout-confirmed.png', fullPage: true });
});
```

| Artifact | Use it when | Caveat |
|---|---|---|
| **Screenshot** | One state matters: final render, error toast, layout | A still frame; hides the path that got there |
| **Video** | A human needs to watch the flow happen | Large; not machine-assertable |
| **Trace** | Debugging timing/flakiness; richest single artifact (DOM snapshots, actions, console, network) | Open with `show-trace`; reviewer needs Playwright |
| **HAR** | Asserting/recording the exact network contract | Strip secrets before committing |

## CLI / TUI capture with tmux

Drive a terminal program non-interactively, then snapshot the screen for both assertions and evidence.

```bash
tmux new -d -s ev -x 200 -y 50          # detached session, fixed geometry = stable snapshot
tmux send-keys -t ev 'myapp --interactive' Enter
sleep 1
tmux send-keys -t ev 'deploy prod' Enter
sleep 2
tmux capture-pane -pt ev > evidence/tui-after-deploy.txt   # -p prints to stdout
tmux kill-session -t ev
grep -q 'Deploy succeeded' evidence/tui-after-deploy.txt   # the assertion (exit 0 = pass)
```

Fixed `-x/-y` geometry keeps the captured frame byte-stable across runs, so the snapshot diffs cleanly and a reviewer regenerates the identical pane.

## Integration / E2E harness

Stand up an **ephemeral** environment with **seeded** data, run the flow against it, tear it down.

```bash
docker compose -f docker-compose.e2e.yml up -d --wait   # --wait blocks on healthchecks
docker compose -f docker-compose.e2e.yml exec -T db psql -f /seed/fixtures.sql
npx playwright test --grep @e2e                          # run the flow against the live stack
docker compose -f docker-compose.e2e.yml down -v         # -v drops volumes: no state leaks
```

Why ephemeral + seeded beats shared staging:

- **Deterministic** — known seed data means the same assertions every run; no "someone changed the staging DB."
- **Isolated** — your run can't be corrupted by, or corrupt, anyone else's.
- **Reproducible by the reviewer** — they run the same three commands and get your result; shared staging is a snowflake they can't reconstruct.
- **Disposable** — `down -v` guarantees a clean slate; no drift accumulating across runs.

## Minimal repro scripts

For a bug or a subtle behavior, commit **one script** that reproduces it end-to-end so the reviewer runs it instead of reading a paragraph.

```bash
#!/usr/bin/env bash
# repro/issue-482-double-charge.sh — run: bash repro/issue-482-double-charge.sh
set -euo pipefail
docker compose -f docker-compose.e2e.yml up -d --wait
trap 'docker compose -f docker-compose.e2e.yml down -v' EXIT
./scripts/seed.sh
curl -sf -X POST localhost:8080/checkout -d @repro/order.json
charges=$(curl -sf localhost:8080/charges | jq 'length')
test "$charges" -eq 1 || { echo "BUG: $charges charges for one checkout"; exit 1; }
echo "OK: exactly one charge"
```

Self-contained, self-cleaning, and its exit code *is* the verdict.

## Attaching artifacts to the PR

Good PR evidence is **the command + what it produced**, pasted together, so the reviewer re-runs nothing on faith:

```
Repro: `bash repro/issue-482-double-charge.sh`
Output: OK: exactly one charge   (was: BUG: 2 charges before fix)
Trace:  evidence/checkout-confirmed.zip  → npx playwright show-trace evidence/checkout-confirmed.zip
```

Attach the screenshot/video/trace **next to** the command that made it. This is also how autonomous loops — the elves runner and long-running agents — leave proof behind: each batch drops its command + artifact into the evidence dir and PR so that after a context compaction the next agent (or a human) can verify the prior step really worked, instead of re-deriving it.

## Prefer / avoid

| Avoid | Prefer |
|---|---|
| Manual click-testing, no artifact left behind | Playwright test that screenshots/traces the same flow |
| Pasting "it works" / "tested locally" | The command and its captured output |
| A screenshot with no way to regenerate it | Screenshot + the exact command/test that produced it |
| Evidence captured against shared staging | Ephemeral `docker compose` run with seeded fixtures |
| A video as the *only* check | An assertion that fails the run, plus the video for humans |

## Anti-patterns

- **Faith-based screenshots** — an image with no command; the reviewer can't tell if it's current or staged.
- **"It works on my machine"** — environment-dependent claims with nothing reproducible attached.
- **Non-re-runnable evidence** — a one-off curl you typed by hand and won't survive; commit it as a script.
- **Snapshot drift** — captures taken with variable terminal size / window size, so they never reproduce byte-for-byte.
- **Secrets in artifacts** — committing a HAR or trace with live tokens/cookies. Redact before attaching.
- **Video instead of assertion** — a 30s clip nobody watches, with no failing check gating the merge.

## Checklist

- [ ] Every visual/interactive/cross-system change has a hard artifact attached.
- [ ] Each artifact ships with the **one command** that regenerates it.
- [ ] Browser flows have an `expect(...)` assertion, not just a screenshot/video.
- [ ] Traces/videos enabled in `playwright.config.ts` (`on` while gathering, `only-on-failure` in CI).
- [ ] E2E runs against an **ephemeral, seeded** environment and tears down with `down -v`.
- [ ] Bugs include a committed repro script whose exit code is the verdict.
- [ ] Snapshots use fixed geometry (tmux `-x/-y`, browser viewport) so they reproduce.
- [ ] No secrets in any committed HAR/trace/log.
- [ ] PR shows command + output side by side; reviewer re-runs nothing on trust.

## Verification

```bash
npx playwright test                          # flow passes; artifacts written to test-results/
npx playwright show-trace trace.zip          # open the trace: inspect actions, DOM, network, console
tmux capture-pane -pt ev                     # print the live pane to confirm the expected text/state
docker compose up --abort-on-container-exit  # run the stack; exit code reflects the E2E result
```

What to look for:

- `playwright test` — exits 0; `playwright-report/` and `test-results/` contain the trace/video/screenshot you intend to attach.
- `show-trace` — the timeline reaches the final asserted state; no unexpected network failures or retries on the way.
- `capture-pane` — the snapshot contains the success string (and the prior failing output, for before/after evidence).
- `docker compose up --abort-on-container-exit` — non-zero exit if any container (test runner included) fails; the run log is the artifact. Pair with `down -v` to confirm clean teardown.

Logic-level proof lives in [test_design.md](test_design.md); the loop that drives red → green before you capture any of this is in [red_green_loop.md](red_green_loop.md).
