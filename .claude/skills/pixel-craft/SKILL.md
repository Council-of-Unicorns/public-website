---
name: pixel-craft
description: House visual style for this product's front end — restrained pixel art and 8-bit animation with quiet typography and high-craft renderings. Use whenever building, styling, reviewing, or animating any UI here: pages, components, hero art, sprites, loading states, icons, transitions, color, or type. Also use when asked for "retro", "pixel", "8-bit", "sprite", "dithering", "palette", or when judging whether a screen looks flashy, generic, or off-brand.
---

# Pixel Craft — House Style

The product looks like a beautifully made small game, not an arcade. Pixel art carries all
the personality; everything around it stays quiet. If a screen feels loud, the fix is almost
never "add more pixel styling" — it is "remove a competing element so the art can land."

## The one-sentence brief

Restrained 8-bit: a limited palette, a strict pixel grid, very little text set cleanly, and
one or two exquisitely crafted animated focal points per screen.

## Ground it in the subject

The company builds a **specialized chip that runs world action models at the edge for humanoid
robots**, with the model architecture etched into silicon (see `docs/pitch.md` and `CLAUDE.md`).
The aesthetic is not nostalgia borrowed from games — it earns its place because the subject and
the medium are the same idea:

- A pixel is the atomic unit of a grid, which is what a die floorplan is. Sprite work and chip
  layout are both "commit to a grid and place every cell deliberately."
- Limited palettes and low frame counts are **constraint-driven design under a hard budget** —
  the exact argument the pitch makes about 40W and 5Hz. The art should feel engineered to fit,
  because that is the company's whole thesis.
- Etching is permanence. Hard edges, no blur, no gradient — nothing soft or provisional.

Useful visual vocabulary, drawn from the subject rather than from arcade clichés: die shots and
floorplans, routing and interconnect traces, wafer grids, packet flow, control loops and
timing diagrams, trajectory paths, robot silhouettes, thermal envelopes, parameter-count scale.
A pixel-art rendering of a chip die or a robot head is on-brand; a coin-op cabinet is not.

Two specific traps to avoid here. First, **do not make it look like a game** — no score
counters, health bars, level select, or dungeon menus, however tempting the medium makes them.
Second, **do not let the retro styling imply the technology is retro.** The read should be
"precision-engineered at the level of individual cells," never "old." When in doubt, resolve
toward the vocabulary of silicon and robotics.

The audience is robotics engineers, silicon people, and deep-tech investors who detect
overclaiming instantly. Concrete numbers (5Hz, 40W, 14B parameters, 2×B200) are the most
persuasive material available — set them as the hero content and let the art frame them,
rather than writing adjectives about ambition.

## Non-negotiables

These are the rules that separate real pixel work from a retro-themed website. Violating any
of them reads as amateur immediately, so treat them as hard constraints.

1. **Integer scaling only.** Art authored at 32×32 displays at 32, 64, 96, 128 — never 100px,
   never `width: 100%` on a sprite. Fractional scaling resamples and destroys the grid.
2. **`image-rendering: pixelated`** on every raster asset, without exception. The browser's
   default smoothing is the single most common way pixel art gets ruined.
3. **Step timing for sprite motion.** `steps(n)`, never `ease` or `linear`. Tweened pixel art
   is the loudest possible tell that the aesthetic is a costume rather than a craft.
4. **Everything snaps to the pixel unit.** Spacing, borders, shadow offsets, type sizes, and
   component dimensions are all whole multiples of `--px`. No fractional values anywhere.
5. **Hard shadows only.** `box-shadow: 4px 4px 0 <ink>`. Zero blur radius. No `border-radius`
   unless it is a deliberate multiple of the pixel unit rendered as a stepped corner.
6. **Pixel font for accents, real font for reading.** Body copy is never set in a pixel face.
   See `references/typography.md` — this is what keeps "simple text" legible.

## What "not too flashy" rules out

The retro genre has a strong gravitational pull toward neon-arcade maximalism. Resist all of
it. Do not produce, and actively remove if inherited:

- Neon glow, bloom, or `text-shadow` halos on anything
- Synthwave purple-to-pink gradients, and gradients generally unless dithered
- CRT scanlines, chromatic aberration, and vignette — at most *one* subtle nod, usually none
- Blinking text, marquees, or looping motion on every element at once
- A pixel border on every box; borders are an emphasis tool, so most elements get none
- Emoji standing in for icons

The house read is closer to a quiet indie game's title screen or a well-made handheld device
UI: lots of calm negative space, a small amount of confident text, and art worth looking at.

## Motion budget

At most **one primary animated focal point per viewport**, plus optionally one slow ambient
loop at low contrast. Everything else holds still. Motion earns attention only when it is
scarce, and a screen where three things move is a screen where nothing is looked at.

Sprite loops run at an 8–12fps feel — for a 6-frame cycle that means roughly a 0.6s duration.
Ambient background loops should cycle slower than 2s and stay low-contrast.

Always honor `prefers-reduced-motion` by freezing sprites to a single representative frame
rather than hiding them; the art should still be present, just static.

## Working method

When building any new surface, work in this order. Jumping straight to layout is what
produces generic results.

1. **Fix the palette first** (`references/palette.md`). Choose 8–16 colors, build hue-shifted
   ramps, and commit. Every later decision references these tokens.
2. **Set the pixel unit and grid** (`references/rendering.md`). Pick `--px`, derive the
   spacing scale from it, and pick the sprite authoring resolution.
3. **Write the copy before styling it.** Short lines, one idea per screen. If a section needs
   a paragraph to explain itself, the art is not doing its job.
4. **Build the art as the focal point**, then lay quiet type and generous space around it.
5. **Look at it.** Use the `webapp-testing` skill to screenshot the running page and actually
   inspect the result — pixel work cannot be verified by reading CSS. Check the grid held at
   the real device pixel ratio, and check the sprite is not being resampled.

For procedural or generative background art (starfields, drifting clouds, subtle particle
fields), the `algorithmic-art` skill covers p5.js technique; keep its output quantized to the
pixel grid and to the house palette rather than accepting its defaults.

For broader UX judgment — accessibility thresholds, touch targets, navigation patterns — the
`ui-ux-pro-max` skill has a searchable database. Its Pixel Art style entry is a useful cross
check, but where it conflicts with this file, this file wins.

## Reference material

Load these on demand rather than reading all of them every time:

- `references/palette.md` — limited palettes, hue-shifted ramps, dithering, contrast
- `references/motion.md` — sprite sheets, `steps()` timing, frame budgets, reduced motion
- `references/typography.md` — pixel-face vs body-face, integer sizing, quiet text layout
- `references/rendering.md` — the pixel grid, integer scaling, canvas/SVG/DPR handling

## Pre-delivery checklist

Before calling any screen done, verify every line:

- [ ] All sprites scaled by a whole-number factor, with `image-rendering: pixelated`
- [ ] Sprite animation uses `steps()`; no tweened pixel motion anywhere
- [ ] Every spacing, size, border, and shadow offset is a multiple of `--px`
- [ ] Palette holds — no colors outside the committed set, no undithered gradients
- [ ] Body copy is in the reading face, not the pixel face, and passes 4.5:1 contrast
- [ ] At most one primary motion focal point in the viewport
- [ ] `prefers-reduced-motion` freezes sprites rather than removing them
- [ ] Screenshotted and visually inspected, not just reasoned about
- [ ] Nothing from the "not too flashy" list crept in
