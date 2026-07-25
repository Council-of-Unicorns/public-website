# Skills

Claude Code skills vendored into this repo so every session — local, cloud, or CI — picks them
up automatically after a clone.

## House style

| Skill | Origin | Notes |
|---|---|---|
| `pixel-craft` | Written for this repo | **Authoritative** for all visual decisions. Where any other design skill conflicts with it, `pixel-craft` wins. |

## Design and front-end

| Skill | Origin | License |
|---|---|---|
| `frontend-design` | [anthropics/skills](https://github.com/anthropics/skills) | LICENSE.txt |
| `webapp-testing` | [anthropics/skills](https://github.com/anthropics/skills) | LICENSE.txt |
| `algorithmic-art` | [anthropics/skills](https://github.com/anthropics/skills) | LICENSE.txt |
| `ui-ux-pro-max` | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) v2.11.0 | MIT |

`ui-ux-pro-max` ships a searchable database (84 styles, 192 palettes, 74 font pairings, 98 UX
guidelines). Query it from the repo root:

```bash
python3 .claude/skills/ui-ux-pro-max/scripts/search.py "<query>" --domain style
```

The upstream `SKILL.md` referenced `${CLAUDE_PLUGIN_ROOT}`, which is only set for plugin
installs. Those paths were rewritten to be repo-root-relative so the skill works vendored. Keep
that patch in mind when upgrading — re-apply it after pulling a new upstream version.

Only the `ui-ux-pro-max` skill directory was vendored, not the full 23MB upstream repo (which
also contains a CLI, screenshots, and six sibling skills). Add those separately if wanted.

## Engineering

From the founder's personal library, [Zarand3r/claude-skills](https://github.com/Zarand3r/claude-skills)
(MIT): `karpathy-guidelines`, `principal-production-engineer`, `strategic-engineering-planner`,
`spec-driven-development`, `implementation-plan`, `test-driven-verification`,
`cpp-systems-internals`, `data-oriented-design`, `python-style`, `system-design-visualizer`,
`auto-research`, and the `elves` autonomous harness.

## Deliberately not installed

- `theme-factory`, `canvas-design`, `brand-guidelines` (anthropics/skills) — generic theme
  presets and Anthropic's own brand identity, both of which pull against a committed house
  aesthetic. `canvas-design` is also 5.6MB and targets posters/PDFs rather than web.
- `web-artifacts-builder` — for claude.ai artifacts specifically, not a production site.
- [`willibrandon/pixel-plugin`](https://github.com/willibrandon/pixel-plugin) — good pixel-art
  craft content, but every skill binds to `mcp__aseprite__*` tools requiring Aseprite (a paid
  desktop app) plus its MCP server. Neither is installed, so the skills would trigger and then
  be unable to act. The durable technique it covers (dithering, hue-shifted ramps, palettes) is
  reproduced in `pixel-craft/references/`, retargeted at CSS, canvas, and SVG.
