# Motion

## The rule that defines the style

8-bit animation is **discrete**. Frames snap; nothing interpolates. In CSS this means
`steps()` and nothing else for sprite motion. A pixel character that slides smoothly across
the screen at 60fps looks wrong in a way most viewers can feel without being able to name, and
it undoes all the craft in the art itself.

## Sprite sheet animation

Author the cycle as a single horizontal strip: `n` frames, each `w × h` at native resolution.
Animate `background-position-x` with `steps(n)`.

```css
.sprite {
  --frame-w: 32px;      /* native frame width  */
  --frame-h: 32px;      /* native frame height */
  --frames: 6;
  --scale: 3;           /* MUST be a whole number */
  --duration: 0.6s;     /* 6 frames / 0.6s = 10fps */

  width:  calc(var(--frame-w) * var(--scale));
  height: calc(var(--frame-h) * var(--scale));
  background-image: url("/art/walk.png");
  background-size: calc(var(--frame-w) * var(--frames) * var(--scale)) auto;
  background-repeat: no-repeat;
  image-rendering: pixelated;
  animation: sprite-cycle var(--duration) steps(var(--frames)) infinite;
}

@keyframes sprite-cycle {
  from { background-position-x: 0; }
  to   { background-position-x: calc(var(--frame-w) * var(--frames) * var(--scale) * -1); }
}
```

The math to get right: the end position travels the **full** sheet width (`n` frames), and
`steps(n)` divides that into `n` holds. This displays frames 0 through n−1 and then wraps —
it never shows a blank frame past the end, which is the usual off-by-one bug here.

## Frame budgets

Low frame counts are correct, not a compromise. The originals were expressive with very few
frames because each one was drawn to read clearly on its own.

| Motion | Frames | Feel |
|---|---|---|
| Idle breathing | 2–4 | ~4–6fps, slow and calm |
| Walk / run cycle | 4–8 | ~8–12fps |
| UI state change | 2–3 | fast, ~15fps, then hold |
| Ambient background | 2–4 | slower than 2s per cycle |

Target an **8–12fps feel** for character motion. Compute duration as `frames ÷ target_fps`.

## Positional motion

When a sprite travels across the screen, quantize the movement to the pixel grid too. Smooth
translation of a stepped sprite is a mismatch that reads as sloppy.

```css
@keyframes drift {
  from { transform: translateX(0); }
  to   { transform: translateX(calc(var(--px) * 40)); }
}
.drifter {
  animation: drift 8s steps(40) infinite;  /* one --px per step */
}
```

Animate `transform` and `opacity` only. Animating `width`, `height`, `top`, or `left` forces
layout on every frame and will stutter, which is doubly visible when motion is stepped.

## Motion budget

One primary focal animation per viewport, plus at most one slow low-contrast ambient loop.
This is a hard limit, not a guideline. Scarcity is the entire reason the animated element gets
looked at, and a screen with three competing loops reads as a busy toy.

UI feedback motion (hover, press, state transitions) is exempt from the count but must be
short — 2–3 frames, finishing under 200ms, then holding still.

## Reduced motion

Freeze to a representative frame rather than removing the art. The composition was designed
with the sprite present, so hiding it leaves a hole.

```css
@media (prefers-reduced-motion: reduce) {
  .sprite {
    animation: none;
    background-position-x: 0;   /* rest frame */
  }
}
```

Pick the rest frame deliberately — the most characterful pose, not necessarily frame 0.

## Canvas alternative

Reach for canvas when motion is procedural (particles, parallax fields, generative
backgrounds) rather than a fixed cycle. Keep the same discipline: draw at native resolution,
scale up by a whole number, and disable smoothing.

```js
const ctx = canvas.getContext("2d");
ctx.imageSmoothingEnabled = false;          // the canvas equivalent of image-rendering
```

Advance procedural motion on a fixed logical tick (e.g. 10 updates/sec) rather than on every
`requestAnimationFrame`, so the result stays stepped instead of drifting into smoothness.
Render positions rounded to whole pixels with `Math.floor` before drawing.
