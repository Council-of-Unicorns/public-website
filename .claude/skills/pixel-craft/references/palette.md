# Palette

## Why the limit matters

A constrained palette is what makes pixel art read as *designed* rather than *filtered*. Old
hardware forced 4, 16, or 64 colors, and the discipline that constraint imposed is the reason
the era's art still looks good. Commit to **8–16 total colors** and use no others. When
something needs to stand out, take a color away from its surroundings rather than adding a
brighter one.

## Hue shifting — the single most important technique

Amateur pixel art builds shadows by lowering the lightness of one hue. Real pixel art shifts
hue as it moves along the ramp: **shadows rotate toward blue/purple and desaturate slightly,
highlights rotate toward yellow/orange and gain saturation.** This mimics how ambient skylight
fills shadows while warm direct light hits the lit faces, and it is the difference between art
that looks flat and art that looks lit.

A correct 5-step ramp for a mid-tone terracotta:

```
darkest   #4A2338   hue ~320  (rotated toward purple, desaturated)
dark      #7A3B22   hue ~18
base      #B5652F   hue ~24
light     #D98E4A   hue ~30
lightest  #F0C176   hue ~38  (rotated toward yellow, saturated)
```

Note the hue travels roughly 40° across the ramp and never sits still. A ramp where every step
shares a hue value is the most common tell of inexperienced work.

Keep ramps to 4–5 steps. More steps invite smooth shading, which fights the medium.

## Starter palette

A restrained, warm-neutral set that suits the house style. Swap the values for the real brand
colors once they exist, but keep the *structure*: a paper ramp, an ink ramp, one warm accent
ramp, one cool accent ramp, used in that order of frequency.

```css
:root {
  /* Paper — backgrounds, most surface area */
  --paper-0: #F2EDE2;
  --paper-1: #E0D8C7;
  --paper-2: #C7BCA6;

  /* Ink — text, outlines, shadows */
  --ink-3:   #8C8172;
  --ink-2:   #4A4453;
  --ink-1:   #2A2536;
  --ink-0:   #16121F;

  /* Warm accent — the single attention color, used sparingly */
  --warm-2:  #7A3B22;
  --warm-1:  #B5652F;
  --warm-0:  #D98E4A;

  /* Cool accent — secondary, for calm/informational states */
  --cool-1:  #2F5E63;
  --cool-0:  #4E8C8A;
}
```

Twelve colors. The accent ramps should cover well under 10% of any screen — that scarcity is
what makes them function as accents at all.

## Dark mode

Do not invert. Build a second committed palette where the paper ramp becomes a deep
purple-shifted ink and the ink ramp becomes a warm off-white, then re-check every contrast
pair. Pixel art with baked-in colors needs either a second sprite variant or a palette chosen
to sit acceptably on both grounds — decide which per asset rather than globally.

## Contrast is still mandatory

The retro aesthetic does not exempt anything from accessibility. Body text needs **4.5:1**
against its background and interactive elements need **3:1**. Pixel faces additionally need
more contrast than their measured ratio suggests, because thin single-pixel stems break up
visually — treat 4.5:1 as the floor for pixel type, not the target.

Never use color alone to carry meaning. In a palette this small, two states can easily be
indistinguishable to a colorblind viewer, so pair color with a shape, icon, or label change.

## Dithering instead of gradients

Smooth CSS gradients break the medium. When a surface needs tonal transition, dither it.

A 50% checkerboard blend between two palette colors, at pixel scale:

```css
.dither-50 {
  background-color: var(--paper-1);
  background-image:
    repeating-conic-gradient(var(--paper-2) 0% 25%, transparent 0% 50%);
  background-size: calc(var(--px) * 2) calc(var(--px) * 2);
}
```

For 25% or 75% densities, and for any multi-step dithered ramp, pre-render the pattern as a
small tiling PNG rather than fighting CSS — you get exact control over the Bayer matrix and it
costs less at paint time. Bayer (ordered) dithering suits flat UI surfaces because its regular
pattern reads as texture; Floyd–Steinberg (error-diffusion) suits photographic or illustrative
art where the noise should be irregular.

Keep dithering subtle. It is a texture, not a feature, and a page where every panel is visibly
dithered has become busy.
