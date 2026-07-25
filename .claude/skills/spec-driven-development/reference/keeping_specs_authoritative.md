# Keeping Specs Authoritative

Covers governance that keeps the spec the single source of truth as requirements and reality change. Load this when reviewing a PR against a spec, handling a requirement change, or when implementation reveals the spec is wrong — so the spec doesn't rot into a lie.

## Doctrine

> A stale spec is worse than no spec: it asserts a contract the code no longer honors, and everyone trusts it until it burns them.

- **Code never silently diverges from the spec.** Divergence is a bug, whether code is wrong or the spec is.
- **When reality and the spec disagree, change the SPEC FIRST** — with rationale and date — **then the tests, then the code.** Always that order.
- **Every behavior change touches the spec.** No behavior PR merges without a spec diff in it (or a linked one).
- **One owner, one document.** The spec is versioned in-repo, reviewed like code, and CI-checked — not a wiki nobody opens.

## When to apply / when to skip

| Apply | Skip |
|---|---|
| Behavior, AC, or invariant changes | Pure refactor, no observable behavior change |
| Implementation contradicts an AC | Typo / comment / formatting |
| New requirement arrives mid-build | Spec already amended this PR |
| Externally-facing contract shifts | Internal-only spike thrown away after |

## Drift detection — signs spec and code diverged

| Signal | What it means | Catch it by |
|---|---|---|
| Test passes but maps to no AC | Behavior exists that nobody spec'd | Require AC ID in every test name/tag |
| AC has no referencing test | Contract unverified or quietly dropped | Orphan-AC grep in CI (see Verification) |
| PR changes behavior, spec untouched | Spec is going stale right now | Reviewer diffs behavior vs spec |
| `TODO`/`FIXME` contradicts an AC | Code admits it violates the contract | Grep TODOs against AC text in review |
| Traceability matrix not updated | Mapping rotted | Matrix is part of the diff, reviewed |

**In review, diff behavior against the spec, not against the old code.** Ask: "Which AC does each changed line serve? Which AC just changed meaning without a spec edit?"

## Change control when requirements change

```
1. Amend spec   → add/edit AC, write rationale + date, bump version
2. Update tests → derive from the new/edited AC (red first)
3. Update code  → make the new tests green
4. Update matrix → AC ↔ test ↔ code stays current
```

- The spec edit and the code edit live in the **same PR** (or the code PR links the spec PR and is blocked on it).
- Reference the AC ID in the commit message: `feat(auth): enforce lockout after 5 fails [AC-12]`.
- See [writing_the_spec.md](writing_the_spec.md) for AC/EARS form and [deriving_code_and_tests.md](deriving_code_and_tests.md) for the matrix.

## When implementation reveals the spec is wrong or impossible

Do **not** code around it. The discovery is data the spec must absorb.

```
STOP
 └─ amend the spec: record the discovered constraint + rationale + date
     └─ if externally-facing → re-confirm with the stakeholder before continuing
         └─ update tests to the corrected AC
             └─ resume implementation
```

A spec that says "respond < 50ms" when the dependency floors at 80ms is a lie the moment you discover it. Fix the AC to the real constraint; don't ship code that silently misses 50ms while the spec still claims it.

## Where the spec lives and how it's linked

- Versioned in-repo: `docs/specs/<feature>.md`, reviewed in PRs, gated by CI.
- Linked from the PR description; AC IDs referenced in commit messages and test names.
- Traceability matrix lives beside the spec and is updated in the same change.

### Prefer / avoid

| Avoid | Prefer |
|---|---|
| Spec in a doc/wiki nobody updates | Spec in-repo, versioned next to code |
| Spec reviewed once, then forgotten | Spec reviewed every PR that touches behavior |
| No link between PR and spec | PR description links spec; commits cite AC IDs |
| Spec correctness unenforced | CI fails on orphan ACs / behavior-without-spec |
| Behavior owner ≠ spec owner, no sync | Same owner edits spec + code in one PR |

## Anti-patterns

- **Write-once spec.** Authored to unblock kickoff, never touched again — drifts into fiction within a sprint.
- **Behavior-without-spec merge.** Feature ships, spec unchanged; the next reader builds on a false contract.
- **"We'll update the spec later."** Later never comes; the diff that knew the rationale is gone.
- **Code-around-the-spec.** Implementer hits a wall, silently changes behavior, leaves the AC asserting the old promise.
- **Split ownership, no sync.** PM owns the spec, devs own the code, neither reconciles — guaranteed divergence.
- **Matrix as afterthought.** Filled in once, never maintained, so it certifies nothing.

## Per-PR checklist

- [ ] Does the diff's behavior match the current spec? (diff against spec, not old code)
- [ ] Are all new/changed behaviors covered by an AC in this (or a linked) PR?
- [ ] Spec edits carry rationale + date; version bumped.
- [ ] Externally-facing changes re-confirmed with the stakeholder.
- [ ] Every changed AC has a derived test (red→green shown).
- [ ] Traceability matrix updated; no orphan ACs, no orphan tests.
- [ ] Commits/tests reference AC IDs.
- [ ] No `TODO`/`FIXME` contradicting a live AC.

## Verification

**CI gate — fail when an AC ID has no referencing test:**
```bash
# Every AC-NNN in the spec must appear in at least one test file.
specs="docs/specs"; tests="tests"
grep -rhoE 'AC-[0-9]+' "$specs" | sort -u > /tmp/spec_acs
grep -rhoE 'AC-[0-9]+' "$tests" | sort -u > /tmp/test_acs
orphans=$(comm -23 /tmp/spec_acs /tmp/test_acs)
[ -z "$orphans" ] || { echo "Orphan ACs (no test):"; echo "$orphans"; exit 1; }
```

**CI gate — fail when behavior changed but no spec diff:**
```bash
# If non-test source under src/ changed, require a change under docs/specs/.
base="origin/main"
code=$(git diff --name-only "$base"... -- src/ | grep -v '_test\|\.test\.' || true)
spec=$(git diff --name-only "$base"... -- docs/specs/ || true)
[ -z "$code" ] || [ -n "$spec" ] || { echo "Behavior changed without a spec diff"; exit 1; }
```

**Find orphan ACs / orphan tests interactively:**
```bash
comm -23 /tmp/spec_acs /tmp/test_acs   # ACs with no test
comm -13 /tmp/spec_acs /tmp/test_acs   # test IDs not in any spec
```

**Diff the spec against the implemented surface:**
```bash
grep -rhoE 'AC-[0-9]+' docs/specs/ | sort -u | wc -l   # ACs declared
grep -rnE 'AC-[0-9]+' tests/ | sort -u                 # where each is exercised
grep -rnE 'TODO|FIXME' src/ | grep -iE 'AC-[0-9]+|spec' # code admitting drift
```

What to look for: zero orphan ACs, zero behavior-without-spec PRs, every AC ID traceable to a test, and no TODO that contradicts a live criterion. Wire the two gates into CI so drift fails the build instead of merging.
