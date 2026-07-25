# Rendering and the grid

## The pixel unit

Everything in the system derives from one value. Pick it once and never compute anything
outside its multiples.

```css
:root {
  --px: 4px;                          /* the base unit — one "art pixel" on screen */

  --space-1: calc(var(--px) * 1);     /*  4px */
  --space-2: calc(var(--px) * 2);     /*  8px */
  --space-3: calc(var(--px) * 4);     /* 16px */
  --space-4: calc(var(--px) * 6);     /* 24px */
  --space-5: calc(var(--px) * 10);    /* 40px */
  --space-6: calc(var(--px) * 16);    /* 64px */
}
```

Every margin, padding, gap, border width, shadow offset, and component dimension references
this scale. A stray `13px` anywhere breaks the alignment that makes the whole thing feel
machined rather than approximate.

## Integer scaling

Pixel art is authored small and displayed large by a whole-number factor. This is the rule
most often broken by responsive layout code, because `width: 100%` on a sprite silently
resamples it at almost every viewport size.

```css
.art {
  --native-w: 64px;
  --scale: 4;                                    /* whole numbers only */
  width: calc(var(--native-w) * var(--scale));
  height: auto;
  image-rendering: pixelated;
}
```

To make art responsive, **change the scale factor at breakpoints** rather than letting width
fluctuate:

```css
.art { --scale: 2; }
@media (min-width: 640px)  { .art { --scale: 3; } }
@media (min-width: 1024px) { .art { --scale: 4; } }
```

`image-rendering: pixelated` is the correct value for upscaling. `crisp-edges` is inconsistently
implemented across browsers and should be avoided.

## Device pixel ratio

Integer CSS scaling stays safe on high-DPI displays because the browser maps 1 CSS px to a
whole number of device pixels (2× or 3×), so the composition remains integral. The trap is a
DPR of 1.5, common on Windows laptops and some Android devices, where a 3× CSS scale lands on
4.5 device pixels. `image-rendering: pixelated` handles this acceptably by nearest-neighbor
sampling, but fine single-pixel detail can still shimmer during motion. Test at 1.5× before
shipping art that depends on hairline detail, and thicken it to two art-pixels if it breaks up.

## Canvas

Separate the logical resolution from the display size and turn smoothing off.

```js
const NATIVE_W = 160, NATIVE_H = 144;   // logical art resolution
const SCALE = 4;

canvas.width  = NATIVE_W;                              // drawing buffer stays small
canvas.height = NATIVE_H;
canvas.style.width  = `${NATIVE_W * SCALE}px`;         // CSS scales it up
canvas.style.height = `${NATIVE_H * SCALE}px`;
canvas.style.imageRendering = "pixelated";

const ctx = canvas.getContext("2d");
ctx.imageSmoothingEnabled = false;
```

Drawing into a small buffer and letting CSS upscale is both more authentic and considerably
cheaper than drawing at full resolution. Round every drawn coordinate with `Math.floor` — a
sprite at x = 10.5 gets sampled across two pixels and blurs.

## SVG

SVG is a good fit for pixel *shapes* — icons, borders, decorative chrome — because it stays
sharp at any DPR and can be recolored with CSS. Keep every coordinate on whole units and
disable anti-aliasing:

```html
<svg viewBox="0 0 16 16" shape-rendering="crispEdges" aria-hidden="true">
  <rect x="2" y="2" width="12" height="12" fill="currentColor"/>
</svg>
```

Set the `viewBox` to the native art resolution and size the element by a whole multiple.
Do not use SVG for detailed illustration — hand-placed rects stop being maintainable quickly,
and raster sprite sheets are the right tool there.

## Borders and shadows

Hard edges only. Blur radius is always zero.

```css
.panel {
  border: var(--px) solid var(--ink-1);
  box-shadow: var(--space-2) var(--space-2) 0 var(--ink-0);   /* offset, no blur */
  border-radius: 0;
}
```

Use borders sparingly — they are an emphasis device, so most elements should have none. If a
layout needs a border on every panel to feel organized, the spacing is doing too little work.

## Asset pipeline

- Export sprites as **PNG-8 with the palette baked in**. Indexed color keeps files tiny and
  guarantees no stray colors slipped in during export.
- **Never** save pixel art as JPEG. Its DCT compression introduces ringing artifacts around
  every hard edge, which is precisely the content pixel art consists of.
- Pack animation frames into a single horizontal strip per cycle rather than separate files —
  one request, and it is what the CSS in `motion.md` expects.
- Do not run pixel assets through a lossy image optimizer or a build-time resizer. Check that
  the framework's image pipeline (Next.js `<Image>`, Vite asset plugins) is not silently
  resampling or re-encoding them; most do by default and will quietly ruin the art.
- Author at the smallest resolution that carries the idea. 16×16 for icons, 32×32 or 48×48 for
  characters, 160×144 (the Game Boy frame) for full scenes is a proven starting point.
