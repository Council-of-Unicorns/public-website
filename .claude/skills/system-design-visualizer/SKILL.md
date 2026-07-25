---
name: system-design-visualizer
description: Create a polished, evidence-traceable HTML + inline SVG system-design review package from existing repo-local design Markdown (system-design docs, specs, RFCs, proposals) for human review. Use when asked to visualize, diagram, or present an existing architecture or technical design. Never invent a design; run the source gate and exit early when no eligible design Markdown exists.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# System Design Visualizer

Turn an **existing, repository-local system-design Markdown specification** into a human-reviewable artifact: a single, self-contained `system-design.html` with inline SVG diagrams, source-grounded narrative, a scoped legend per diagram, and an embedded machine-readable manifest.

> This skill is a **visualization and review layer, not a system-design author.** The repository's Markdown is the only source of truth. Never create architecture, requirements, APIs, schemas, failure behavior, targets, or contracts the source does not state.

## Invocation

Run after a design exists. `$ARGUMENTS` may carry an output path or focus area. Default output: `docs/system-design/visuals/system-design.html`.

Canonical artifact policy: `system-design.html` (inline SVG) is the source of truth. PDF / standalone SVG / PNG / Excalidraw are derivatives produced **only on explicit request**; Excalidraw follows `templates/EXCALIDRAW_EXPORT_CONTRACT.md`.

## Hard gate — find a source design before doing anything else

1. From the target repository root, run:

   ```bash
   python3 "${CLAUDE_SKILL_DIR}/scripts/find_system_design_sources.py" .
   ```

   It reports eligible Markdown (system-design docs, specs, RFCs, proposals, HLDs) and *why* each qualified. Read **every** reported source before drafting anything.

2. If it exits non-zero (no eligible source), **stop.** Do not create HTML, a placeholder diagram, or speculative sections. Respond exactly:

   > Cannot create the system-design visualization because this repository does not contain an eligible system-design Markdown source. Generate or add the system design first, then run this skill again. I did not create a placeholder architecture because that would introduce ungrounded design decisions.

   Include the checked paths from the script output.

3. If sources exist but omit a required topic, do not infer it. Keep the section, mark it `Not specified in the design sources`, add a visible source-gap note, and omit diagrams that would need invented content.

## Source grounding (essentials)

- Source Markdown is the **only** authority for system-specific claims. Every heading, paragraph, table row, node, edge, label, numeric target, tradeoff, and operational claim must trace to a source path + heading.
- **Preserve modality.** If the source says `proposed`, `target`, `may`, `TBD`, or `open question`, keep it — do not present it as settled.
- Condense and reorganize freely; never change meaning. Generic doc scaffolding, legend conventions, and a11y annotations may come from this skill but must not imply system facts.
- Do **not** fill gaps from README prose, source code, issues, external research, or your own knowledge unless the user explicitly expands the source set.
- Add `<details class="source-notes">` under each substantive section, and `sourceRefs` on every manifest item.

For source selection, conflicts, omissions, the claim ledger, and traceability markup, read **`references/SOURCE_GROUNDING.md`**.

## Required review package

One standalone HTML document in this reading order. Sections **1–3 and 7–10 are mandatory** (a mandatory section with no source content carries an explicit source-gap note). Diagrams appear **only when source-backed facts support them.**

1. Cover + executive summary — purpose, status, decision requested, source inventory.
2. High-level requirements — functional requirements, non-goals, success criteria.
3. Constraints and assumptions — latency, scale, budget, compliance, environment, compatibility, team, timeline (keep assumptions separate).
4. System context diagram — actors, external systems, boundaries, runtime interactions only.
5. Runtime architecture diagram — deployable components, datastores, queues/topics, runtime communication only.
6. Critical sequence diagram(s) — one per source-documented critical path (retries/timeouts/fallbacks only if specified).
7. Data flow and ownership — origin, transformation, systems of record, readers/writers, retention/deletion, sensitive data where documented.
8. API, event, and contract reference — endpoints, RPCs, events, schemas, auth, timeout/retry, idempotency, ordering.
9. Data model reference — entities, key fields, relationships, ownership, indexes, lifecycle, schema/version contracts.
10. Reliability and operational behavior — dependency failures, timeout ownership, retries, idempotency, backpressure, degraded modes, observability, rollback.
11. Performance and scaling — targets, bottlenecks, throughput, concurrency, queue behavior, capacity, cost.
12. Deployment / availability — only when the source has the facts.
13. Open questions, decisions, and source gaps — preserve unresolved items.
14. Traceability appendix — source files/headings ↔ output sections and diagram elements.

## Diagram discipline

**One diagram answers one question.** Never mix runtime traffic, static dependencies, deployment topology, data lineage, and state transitions in one picture — a reader must never have to guess what a line means. Pick the view with the diagram chooser in `references/VISUAL_LANGUAGE.md`.

Non-negotiable arrow rules (full grammar + legends in `references/VISUAL_LANGUAGE.md`):

- Every material edge has a **verb-bearing label** (protocol/endpoint/event/data object where helpful); never `uses`, `connects`, `syncs`, or an unlabeled line.
- Solid + filled arrowhead = runtime (sync call, async via a **first-class queue/topic node**, or write/read at a datastore). Dashed + open arrowhead = static dependency **only**, and only in a dependency diagram.
- Separate directed edges for independent read and write; never a double-headed arrow for both.
- Arrows never mean ownership, grouping, colocation, or trust — use containers and labels.
- Color is never the only semantic cue.

## HTML / SVG standard

Start from `templates/system-design-template.html`. The artifact must be **self-contained** (no CDN, external font, iframe, remote image, or network dependency), semantic, accessible, responsive, printable, and use inline SVG only. Each diagram section co-locates title, question answered, source-backed takeaway, diagram, and legend.

Every SVG: a `viewBox`, `<title>` + `<desc>`, stable IDs on meaningful nodes/edges, selectable `<text>` labels (never paths/raster), arrows behind nodes, labels above arrows. Place nodes on the **coordinate grid** in `references/VISUAL_LANGUAGE.md` rather than freehand — it is the main defense against overlaps. Embed a `system-design-manifest` JSON block (diagrams, nodes, edges, legends, sourceRefs). Distinguish source-backed facts, assumptions, and gaps both visually and textually. Restrained editorial design: whitespace, readable system fonts, clear hierarchy, high contrast, minimal color, no decorative gradients.

## Workflow

1. **Discover + validate sources.** Run the hard gate; read every source; extract a claim → source(file+heading) map.
2. **Content inventory.** Private matrix for requirements, constraints, components, interfaces, data, reliability, performance, deployment, open questions — each field `source-backed` or `not specified`.
3. **Select the minimum diagram set.** Never draw a diagram that needs facts the sources lack.
4. **Write edge sentences first.** Every edge as a source-backed sentence (`Gateway calls Job Service via HTTPS POST /jobs`) before any SVG placement.
5. **Build diagrams** on the coordinate grid: one question each, mandatory arrow vocabulary, standalone legend.
6. **Build reference sections** straight from the inventory. Do not turn omissions into recommendations.
7. **Add provenance.** Source notes per section; `sourceRefs` on every manifest node, edge, table row, and gap.
8. **Validate to green (gate).** Run:

   ```bash
   python3 "${CLAUDE_SKILL_DIR}/scripts/validate_system_design_html.py" path/to/system-design.html
   ```

   Fix every reported error and re-run until it prints `VALIDATION PASSED`. Then open the file in a browser at desktop and narrow widths and check print preview. **Do not present the artifact until the validator exits 0.**

## Completion criteria

Deliver only when all hold:

- The hard source gate passed; every system-specific claim and label is source-backed or explicitly marked a source gap.
- Requirements, constraints, API/contracts, data model, reliability, and performance sections are present.
- Each included diagram has one question, a visible legend, labeled edges, no mixed vocabulary; runtime / dependency / data-flow / deployment semantics are separated.
- The HTML is self-contained, accessible, responsive, printable, and **`validate_system_design_html.py` exits 0**.
- Excalidraw (or any derivative) was created only if explicitly requested.

## Supporting files

- `references/SOURCE_GROUNDING.md` — source selection, claim ledger, conflicts, omissions, traceability markup.
- `references/VISUAL_LANGUAGE.md` — diagram chooser, node/edge grammar, legends, coordinate grid, a11y, review questions.
- `templates/system-design-template.html` — canonical offline HTML/SVG shell (passes the validator as-is).
- `templates/EXCALIDRAW_EXPORT_CONTRACT.md` — derivative export rules, on request only.
- `scripts/find_system_design_sources.py` — mandatory source-gate scanner (recognizes design docs, specs, RFCs, proposals).
- `scripts/validate_system_design_html.py` — structural, a11y, manifest, and provenance validation.
- `scripts/test_scripts.py` — smoke test for the source-gate scanner.
- `examples/visual-language-reference.html` — worked runtime + dependency diagrams to copy from.
