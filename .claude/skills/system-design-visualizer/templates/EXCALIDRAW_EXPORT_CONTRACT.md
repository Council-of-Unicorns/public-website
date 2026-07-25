# Excalidraw Export Contract

## Status

Excalidraw is a **generated, editable derivative**. The canonical artifact remains `system-design.html` with inline SVG and its embedded semantic manifest.

Only use this contract when the user explicitly asks to export or convert the HTML review package to Excalidraw.

## Inputs

Required:

```text
system-design.html
```

The source must contain:

1. Inline SVG for every diagram to be converted.
2. A valid `system-design-manifest` with format `system-design-html-svg/v2`.
3. Stable SVG IDs for every meaningful node and edge.
4. `sourceRefs` for diagram, node, and edge semantics.
5. A visible per-diagram legend.

If any requirement is missing, stop and report the exact missing element. Do not infer semantics from color, proximity, or raster pixels.

## Outputs

```text
generated/excalidraw/
├── 01-context.excalidraw
├── 02-runtime-architecture.excalidraw
├── 03-critical-sequence.excalidraw
├── ...
└── export-report.md
```

Create one editable scene per included diagram. Omit absent diagrams. Never create an empty derivative simply because a template names a view.

## Mapping

| HTML/SVG source | Editable Excalidraw representation |
|---|---|
| Service/client/worker group | rounded rectangle + editable text, grouped |
| Datastore cylinder | rectangle + editable ellipses + text, grouped |
| Queue/topic | narrow rectangle + divider lines + text, grouped |
| Boundary | large unfilled rectangle + boundary label |
| Edge | directed arrow with line style selected from manifest `kind` |
| Edge label | editable text next to arrow |
| Legend | editable arrows/shapes/text that preserve source meaning |

## Semantic edge mapping

| Manifest kind | Excalidraw line | Required treatment |
|---|---|---|
| `sync` | solid, end arrowhead | preserve request/API/protocol label |
| `async` | solid, end arrowhead | preserve `async:` label and queue/topic routing |
| `write` | solid, end arrowhead | arrow enters datastore; preserve write verb |
| `read` | solid, end arrowhead | arrow leaves datastore; preserve explicit read label |
| `dependency` | dashed, open/end arrowhead | only in a dependency diagram |
| `data` | solid, end arrowhead | preserve named data object/transformation label |
| `transition` | solid, end arrowhead | preserve state event/condition label |
| `network-path` | solid, end arrowhead | preserve protocol/boundary label |

## Conversion rules

1. Parse semantic meaning from the manifest and geometry from SVG; do not draw from a screenshot.
2. Preserve SVG viewBox coordinates where practical; add a 40-unit margin.
3. Keep the source reading order and relative placement. Do not auto-layout into a different topology.
4. Keep edge paths behind node groups and labels above arrows.
5. Preserve all node/edge IDs in element metadata or the export report.
6. Make text editable; do not convert text into paths.
7. Keep every legend visible in the scene overview.
8. Do not reverse-convert manual Excalidraw changes into HTML automatically. Apply accepted intent to canonical HTML, then regenerate.

## Validation report

Create `generated/excalidraw/export-report.md`:

```text
Canonical source: system-design.html

Diagram: runtime
Source nodes: 8
Generated semantic node groups: 8
Source edges: 10
Generated arrows: 10
Legend items: 4 / 4 preserved
Source references preserved: 18 / 18
Approximations: Datastore uses editable rectangle + ellipses.
Manual follow-up needed: none
```

Fail the export if any manifest node or edge is missing, any edge label is absent, the legend is absent, or semantic line styles differ from the manifest.
