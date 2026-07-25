# Source Grounding and Traceability

## Scope

The visualization turns local system-design Markdown into a review artifact. It does not independently design the system. The design source is the authority; the HTML is a derived presentation of it.

## Eligible source selection

Use the output of `scripts/find_system_design_sources.py` as the initial source set. Inspect every qualifying file. Accept a file only if it contains system-design evidence, not just incidental mentions of architecture.

Typical eligible evidence includes:

- requirements, non-goals, or success criteria;
- architecture, components, services, data stores, queues, deployment, or trust boundaries;
- APIs, events, schemas, contracts, or data models;
- latency, scale, performance, reliability, security, operations, tradeoffs, or rollout behavior.

Do not use these unless the user explicitly adds them to the source set:

- `README.md` marketing summaries;
- source code, tests, or generated config;
- tickets, PR comments, chat logs, and issue threads;
- unrelated ADRs;
- external documentation or web research.

## Claim ledger

Before authoring, build a private ledger like this:

| Claim ID | Derived content | Status | Source path | Source heading | Used in |
|---|---|---|---|---|---|
| R-01 | Jobs must be idempotent by request ID. | source-backed | `docs/system-design/jobs.md` | `Reliability` | API table; sequence edge |
| P-01 | p95 latency target is 500 ms. | source-backed | `docs/system-design/jobs.md` | `Performance` | performance section |
| G-01 | Retention policy is unspecified. | source gap | — | — | data ownership section |

Never surface the private ledger verbatim unless the user requests it. Use it to create precise HTML source notes and manifest references.

## How to derive prose

You may:

- condense repetitive passages;
- reorganize material by reader task;
- rephrase for clarity without changing modality;
- combine facts from multiple sources when they are compatible;
- use standardized diagram labels such as `writes`, `read result:`, and `async:`.

You may not:

- infer a component, interface, queue, schema, target, retry policy, or security boundary from common practice;
- convert a source open question into a decision;
- resolve conflicting documents silently;
- attach a numeric target that the source does not state;
- use an implementation detail from code as if it were a design commitment.

## Source conflicts

When sources conflict:

1. Preserve both positions and identify the conflict in an `Open questions and source gaps` section.
2. Cite the exact paths and headings for each position.
3. Do not choose the newer-looking document unless the source itself identifies it as superseding the other.
4. Do not draw a single definitive edge or table row that conceals the disagreement.

## Source gaps

When a mandatory section lacks source-backed content, use this exact pattern:

```html
<div class="source-gap" role="note">
  <strong>Not specified in the design sources.</strong>
  This visualization does not infer a value or mechanism for this topic.
</div>
```

A source gap is not an invitation to design. It preserves a reviewable absence.

## Traceability markup

### Human-readable source notes

Place this immediately below each substantive section:

```html
<details class="source-notes">
  <summary>Sources</summary>
  <ul>
    <li><a href="../jobs.md#reliability">docs/system-design/jobs.md — Reliability</a></li>
  </ul>
</details>
```

Use repository-relative links. If a Markdown renderer cannot create stable heading anchors, show the file path and heading text anyway.

### Semantic manifest source references

Every node and edge must carry at least one source reference:

```json
{
  "id": "gateway-to-jobs",
  "kind": "sync",
  "from": "gateway",
  "to": "job-service",
  "label": "HTTPS POST /jobs",
  "sourceRefs": [
    {"path": "docs/system-design/jobs.md", "heading": "API"}
  ]
}
```

Use the same structure for `sections`, `tables`, and `gaps` in the manifest.

## Documentation hierarchy

Use this order to make the package reviewable:

1. Decision-oriented cover
2. Requirements and non-goals
3. Constraints and assumptions
4. Diagrams
5. API/contracts
6. Data model/ownership
7. Reliability and performance
8. Open questions/gaps
9. Traceability appendix

Every system-specific label in the diagrams must be supported by the same source ledger as prose.
