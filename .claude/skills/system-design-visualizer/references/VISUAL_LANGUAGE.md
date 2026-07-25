# Visual Language Reference

## Non-negotiable rule

**One diagram answers one question.** A reader must not have to infer whether a line is a runtime call, a static dependency, data movement, deployment containment, or a state transition.

## Diagram chooser

| Need to explain | Draw this | Do not combine with |
|---|---|---|
| Actors, vendors, external systems, trust boundaries | Context | internal service detail |
| Runtime services, queues, stores, external calls | Runtime architecture | code imports, deployment regions |
| Timing, return values, retries, timeout ownership | Sequence | general system topology |
| Origin, transformation, storage, retention, deletion | Data flow / ownership | API dependency graph |
| Package/interface/schema imports | Dependency | runtime API calls |
| Region/AZ/VPC/GPU/replica placement | Deployment / availability | business workflow detail |
| Valid lifecycle states | State machine | data lineage |

## Node grammar

| Kind | SVG form | Required label treatment |
|---|---|---|
| Person/device/client | outlined box or simple icon + text | role, not a vague brand label |
| Deployable service | rounded rectangle | service name + optional concise responsibility |
| Worker | rounded rectangle with `Worker` subtitle | name + background role |
| Datastore | cylinder | store name + `system of record` when stated |
| Queue/topic | narrow box with divider lines | `Topic:` or `Queue:` prefix |
| External system | outlined rectangle with `External` tag | owner/vendor where stated |
| Boundary | light container with heading | trust, owner, region, tenant, or deployment boundary |
| Code module | plain rectangle | only in dependency view |

## Edge grammar

| Kind | SVG style | Direction | Label form | Allowed in |
|---|---|---|---|---|
| `sync` | solid line, filled arrowhead | caller → callee | `HTTPS POST /v1/jobs`, `gRPC Generate` | context, runtime, sequence |
| `async` | solid line, filled arrowhead; route through topic/queue | producer → topic → consumer | `async: publishes FrameReady`, `async: consumes FrameReady` | runtime, sequence |
| `write` | solid line, filled arrowhead | service → datastore | `writes transcript` | runtime, sequence |
| `read` | solid line, filled arrowhead | datastore → service for result in runtime; request/return separately in sequence | `read result: recent turns` | runtime, sequence |
| `data` | solid line, filled arrowhead | producer → consumer | `H.265 chunks`, `redacted telemetry` | data flow |
| `dependency` | dashed line, open arrowhead | dependent → dependency | `imports AuthClient interface` | dependency only |
| `transition` | solid line, filled arrowhead | state → state | `payment authorized` | state machine |
| `network-path` | solid line, filled arrowhead | traffic direction | `mTLS gRPC` | deployment / availability |

### Arrow rules

1. Label every material edge.
2. Draw separate arrows for independent reads and writes.
3. Do not use `connects`, `uses`, `data`, or `syncs` as labels.
4. Do not use a double-headed arrow unless the source describes a genuine symmetric relationship.
5. A topic/queue is a first-class node for durable async traffic.
6. A dashed dependency arrow never appears in a runtime diagram.
7. An arrow does not mean ownership, containment, co-location, or trust; represent those with containers or labels.
8. Direction follows the request, message, or data movement—not whichever layout looks tidier.

## Required legends

Each SVG carries only the legend entries relevant to its own grammar.

### Runtime architecture

```text
Legend
──► synchronous runtime call
──► async message; label begins async: and routes through a queue/topic
──► write when arrow enters a datastore
──► read result when arrow leaves a datastore
```

### Data flow

```text
Legend
──► movement of a named data object or transformed artifact
Cylinder persistent store
Queue durable asynchronous transport
```

### Dependency

```text
Legend
- - -▷ static import, interface use, schema dependency, or build-time dependency
```

## SVG layout rules

- Prefer left-to-right for requests/data movement and top-to-bottom for time in a sequence.
- Keep the primary path visually straight. Use orthogonal or gentle curved routes only to avoid collisions.
- Maintain whitespace around labels; never allow labels to cross node borders or other labels.
- Place edge paths behind nodes; labels above paths.
- Avoid more than roughly 10–14 nodes in a first-pass architecture view. Split by concern instead.
- Use containers sparingly: a boundary must state what it means.
- Use shapes and text in addition to restrained color, so grayscale output remains legible.
- Include `<title>` and `<desc>` for every SVG, and make all SVG text selectable.

### Coordinate grid — place nodes on a grid, don't freehand

Freehand coordinates are the main source of overlapping, unreadable diagrams. Snap to a grid instead. For a left-to-right runtime/context view use `viewBox="0 0 1120 H"` and this scheme:

| Element | Rule |
|---|---|
| Column lanes (flow direction) | Node **centers** at x = 140, 380, 620, 860, 1040 (≈240 px pitch). One process stage per lane. |
| Row bands (parallel components) | Node centers at y = 120, 240, 360, 480 (120 px pitch). Datastores/queues one band below their writer. |
| Node box | 168 × 72, rounded rect, centered on its (lane x, band y); text centered inside. |
| Edge path | Straight line/curve between node centers, clipped at box edges. Draw it **before** the boxes. |
| Edge label | Centered on the edge midpoint, `text-anchor="middle"`, with a small opaque background rect behind it so it stays legible where it crosses a line. Draw **after** the boxes. |
| Draw order (z-order) | 1) edge paths → 2) node boxes → 3) node text → 4) edge-label backgrounds + labels. This is what makes "arrows behind nodes, labels above arrows" actually true. |

For a **sequence** view, swap axes: lifeline heads across the top at the column x-values, time increasing top-to-bottom through the row bands; each message is a horizontal arrow at the next band.

A worked, copy-adaptable version of the runtime and dependency views (with these coordinates, markers, and legends) is in `examples/visual-language-reference.html` — start from it rather than an empty canvas.

## Review questions

For each included diagram, verify:

- Can a reviewer name the exact question it answers?
- Can they explain every arrow from its label and legend?
- Is every system-specific node/edge source-backed?
- Can the view be understood without looking at another diagram?
- Does the visual hierarchy reveal the main path before secondary detail?
