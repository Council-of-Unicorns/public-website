# Typography

## The pairing rule

**Pixel faces are for accents. Reading text is never set in a pixel face.**

This is what makes "simple text" work. Retro sites that set body copy in Press Start 2P become
exhausting within a paragraph — the uniform stroke weight and blocky counters give the eye no
shape cues, so reading speed collapses. Reserve the pixel face for short strings the eye
*recognizes* rather than *reads*, and set everything else in a clean, well-rendered face.

**Pixel face** — wordmark, section labels, buttons, numerals, nav items, small UI chrome.
Never more than a few words at a time.

**Reading face** — headlines, body copy, anything over roughly five words.

The contrast between the two is itself a design device: the pixel face signals "this is part
of the machine," the reading face signals "this is a person talking to you."

## Choosing the faces

For the pixel face, prefer one with a documented native pixel size:

- **Press Start 2P** — 8px native. Very wide, very blocky. Strong character, use at small sizes.
- **Silkscreen** — 8px native. Narrower and more legible than Press Start 2P.
- **Departure Mono** — 11px native. Monospaced, more refined and modern; suits the restrained
  house style particularly well.
- **Pixelify Sans** — variable, softer and friendlier, less strictly retro.

For the reading face, choose something with excellent screen rendering and a neutral voice so
it recedes behind the art: a humanist sans (Inter, Public Sans, Söhne) or a sturdy text serif
if the product wants more warmth. Avoid anything with strong personality — it will compete
with the sprites.

## Integer sizing is mandatory

A pixel face renders correctly **only at whole multiples of its native size**. Press Start 2P
at 8px native is correct at 8, 16, 24, 32, 40. At 20px it lands between grid positions and the
glyphs get resampled into blur — the same failure mode as fractionally scaling a sprite.

```css
:root {
  --pixel-native: 8px;             /* the chosen face's native size */
}
.label   { font-size: calc(var(--pixel-native) * 1); }   /*  8px */
.button  { font-size: calc(var(--pixel-native) * 2); }   /* 16px */
.display { font-size: calc(var(--pixel-native) * 3); }   /* 24px */
```

Line height for pixel type must also be a whole pixel value — use a unitless multiplier only
if it resolves to an integer, otherwise state it in px directly. Letter-spacing likewise: whole
pixels or zero, never `0.05em`.

Never apply faux styling to a pixel face. Synthetic bold and synthetic italic are computed by
smearing and skewing the outline, which destroys the grid. If you need emphasis, change color,
change size by a whole step, or swap to a different weight that actually ships as its own file.

## The reading face is unconstrained

Body text should be set well by normal typographic standards, not forced onto the pixel grid.
It needs comfortable proportions more than it needs thematic consistency.

- Body size 16px minimum, 17–18px is often better
- Line height 1.5–1.6
- Measure of 60–75 characters; on a sparse page, 45–60 reads better
- Left-aligned, never justified

Rounding body leading to whole pixels is a reasonable nicety, but do not compromise legibility
to achieve it.

## Writing simple text

The style asks for very little copy, which raises the bar on each word.

- **One idea per screen.** If a section needs two paragraphs to land, it is two sections, or
  the accompanying art is not carrying its share.
- **Short lines.** Break headlines manually at meaningful phrase boundaries rather than letting
  them wrap arbitrarily.
- **Cut hedging.** In a sparse layout every word is inspected, so "we're building something
  that helps teams maybe move faster" reads far weaker than it would in dense copy.
- **Sentence case** for headlines. ALL CAPS in a pixel face is acceptable for short labels but
  becomes shouty fast.
- **Generous space.** Whitespace around text is what signals confidence; crowding a headline
  against the art undercuts both.

## Accessibility

Pixel faces need more contrast than their measured ratio implies, because single-pixel stems
visually fragment at small sizes. Treat **4.5:1 as the floor** for pixel type regardless of
size, and prefer more.

Set a real `font-family` fallback chain. Pixel fonts are often loaded from a CDN and, if the
request fails, an unstyled fallback at the same size will badly break the layout — pick a
fallback with similar metrics and test with the webfont blocked.
