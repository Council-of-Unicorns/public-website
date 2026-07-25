# System Design Visualizer — Claude Code Skill

A visualization-first Claude Code skill that turns existing **system-design Markdown** into a polished, reviewable **HTML + inline SVG** design package.

## What it does

- Requires an eligible repository-local system design before it starts.
- Stops rather than inventing an architecture when no source design Markdown exists.
- Grounds all system-specific narrative, diagrams, APIs, data models, reliability, and performance claims in the source documents.
- Produces one self-contained `system-design.html` with separate diagrams, per-diagram legends, source notes, and a machine-readable semantic manifest.
- Supports optional, derivative PDF/SVG/PNG/Excalidraw export after the canonical HTML package is complete.

## Install in Claude Code

Claude Code discovers project skills under `.claude/skills/<skill-name>/SKILL.md` and personal skills under `~/.claude/skills/<skill-name>/SKILL.md`.

```bash
mkdir -p .claude/skills/system-design-visualizer
cp -R . /path/to/your/repo/.claude/skills/system-design-visualizer/
```

Then invoke:

```text
/system-design-visualizer
```

Optionally pass a focus or output instruction:

```text
/system-design-visualizer create the review artifact at docs/architecture/payment-system.html
```

## Package contents

```text
system-design-visualizer/
├── SKILL.md
├── README.md
├── references/
│   ├── SOURCE_GROUNDING.md
│   └── VISUAL_LANGUAGE.md
├── templates/
│   ├── system-design-template.html
│   └── EXCALIDRAW_EXPORT_CONTRACT.md
├── scripts/
│   ├── find_system_design_sources.py
│   ├── validate_system_design_html.py
│   └── test_scripts.py
└── examples/
    └── visual-language-reference.html
```

## Canonical output policy

| Format | Role |
|---|---|
| HTML + inline SVG | Canonical source and primary review artifact |
| PDF | Optional frozen circulation/print derivative |
| SVG / PNG | Optional extracted derivative |
| Excalidraw | Editable derivative generated only on explicit request |

## Core guarantee

The skill never treats a visualization as a substitute for a missing design document. It reports the absence of eligible design sources and exits before creating any architecture, requirements, API, or operational behavior.
