---
version: "1.0"
name: françoise
description: >
  The visual identity for françoise, a language pen-pal you write to abroad.
  Drawn from mid-century American travel magazine Holiday (1946–77, art
  director Frank Zachary): color-forward modernism on cool cream paper, editorial
  type at scale, and a correspondence metaphor — postcards, stamps, postmarks.
  Print-like depth (rules and deboss, not soft shadows). The picture is the
  layout.
colors:
  paper: "#EDEBE4"        # cool cream ("oyster") — the base ground everywhere; never pure white
  paperShade: "#E3DFD4"   # recessed/raised paper for cards and wells
  ink: "#23201C"          # warm near-black — primary text and rules
  inkMuted: "#6B6355"     # secondary text, captions
  rule: "#C8B896"         # hairline tan — borders, frames, dividers
  teal: "#0E7C7B"         # Adriatic teal — primary accent
  coral: "#E2603F"        # terracotta coral — energy, calls to action
  ochre: "#E0A63C"        # sun ochre — highlights, focus
  navy: "#234A6B"         # ink-navy — depth, headings on color blocks
  olive: "#5C7A3D"        # supporting green
  vermilion: "#C8452E"    # postmark red — stamps, alerts
  focus: "{colors.ochre}"
  success: "{colors.olive}"
  error: "{colors.vermilion}"
typography:
  masthead:
    fontFamily: "Fraunces"
    fontSize: "64px"
    fontWeight: 600
    lineHeight: 1.0
    letterSpacing: "-0.02em"
  display:
    fontFamily: "Fraunces"
    fontSize: "40px"
    fontWeight: 600
    lineHeight: 1.05
    letterSpacing: "-0.01em"
  heading:
    fontFamily: "Fraunces"
    fontSize: "24px"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "0"
  body:
    fontFamily: "Work Sans"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: "0"
  bodyLarge:
    fontFamily: "Work Sans"
    fontSize: "18px"
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: "0"
  caption:
    fontFamily: "Work Sans"
    fontSize: "13px"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "0.02em"
  postmark:
    fontFamily: "Courier Prime"
    fontSize: "12px"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "0.08em"
rounded:
  none: "0"
  sm: "2px"
  md: "4px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "40px"
  xxl: "64px"
  xxxl: "96px"
components:
  button:
    background: "{colors.ink}"
    color: "{colors.paper}"
    radius: "{rounded.sm}"
    padding: "12px 20px"
    font: "{typography.caption}"
    hoverShadow: "4px 4px 0 {colors.teal}"
  buttonAccent:
    background: "{colors.coral}"
    color: "{colors.paper}"
    hoverShadow: "4px 4px 0 {colors.ink}"
  buttonSecondary:
    background: "transparent"
    color: "{colors.ink}"
    border: "1px solid {colors.ink}"
  input:
    background: "{colors.paper}"
    border: "1px solid {colors.rule}"
    color: "{colors.ink}"
    radius: "{rounded.sm}"
    focusBorder: "1px solid {colors.ochre}"
    padding: "10px 12px"
  postcard:
    background: "{colors.paperShade}"
    border: "1px solid {colors.rule}"
    radius: "{rounded.none}"
    padding: "{spacing.lg}"
  masthead:
    font: "{typography.masthead}"
    color: "{colors.ink}"
  stamp:
    background: "transparent"
    color: "{colors.vermilion}"
    border: "1px dashed {colors.vermilion}"
    font: "{typography.postmark}"
    padding: "4px 8px"
---

# françoise — design system

## Overview (Brand & Style)

françoise is a friend who writes to you from somewhere abroad. The identity
borrows from **Holiday** magazine's mid-century travel modernism: it should feel
like a beautifully art-directed periodical about the romance of going places —
warm, literary, cosmopolitan, and unhurried.

Two ideas govern everything:

- **The picture is the layout.** Compose with scale, color, and generous space,
  not decoration. A strong element (a masthead, a color block, a persona's
  place) carries the page; type stays tight and sweet around it.
- **Correspondence.** The product is letters between friends. Lean on the
  vocabulary of the post — postcards, stamps, postmarks, cancellation marks,
  par avion borders, itineraries. It makes the language-abroad concept literal
  and gives every surface a motif to reach for.

The mood is print, not app: paper you can almost feel, ink that sits *in* the
page, color used with confidence.

## Colors

A cool **cream ("oyster") paper** base (`paper`) is the ground for the entire product —
never pure white. Text and rules are a warm near-black (`ink`). Against that
neutral, a saturated travel palette does the talking in confident blocks:
`teal`, `coral`, `ochre`, and `navy`, with `olive` and `vermilion` in support.

- Use one dominant accent per view; let color arrive in blocks, not confetti.
- `coral` leads calls to action; `teal` is the everyday primary; `ochre` marks
  focus and highlights; `navy` grounds headings on color fields.
- `vermilion` is reserved for the postal register — stamps, postmarks, alerts.
- `rule`/`paperShade` carry structure (frames, dividers, recessed wells) so
  color never has to.

State colors are drawn from the palette itself (`success` = olive, `error` =
vermilion, `focus` = ochre) so the system never introduces off-brand hues.

## Typography

An editorial pairing across three roles:

- **Fraunces** (variable, high-contrast "old style") for **masthead / display /
  heading** — the magazine voice. Set it large and tight; let it be the picture.
- **Work Sans** (humanist sans) for **body / caption** — clean, calm, and highly
  readable at a comfortable measure (~66ch).
- **Courier Prime** (typewriter) for the **postmark** role — stamps, dates,
  CEFR badges, cancellation marks. Uppercase, tracked out; used sparingly for
  correspondence flavor.

Rules: display type is tight (negative tracking) and big; body type is roomy
(1.6 line-height). Never set body in the display face, and never stretch the
typewriter face into running text.

## Layout & Spacing

Editorial and generous. An 8px-derived scale (`xs`…`xxxl`) with real air at the
top end — pages breathe like magazine spreads. Prefer a strong asymmetric grid
and full-bleed color/masthead panels over centered boxes.

- Establish a clear focal element per view; give it room.
- Reading content sits on a constrained measure; chrome can go wide.
- The landing page is a *sequence of magazine covers* — full-bleed panels, each
  its own composition.

## Elevation & Depth

Print, not Material. Depth comes from the page, not from blur:

- **Hairline rules** (`rule`) and **frames** for structure.
- **Deboss**: a 1px light-over-dark inset to seat inputs and wells into the
  paper.
- **Block shadow**: a hard, offset shadow in an accent (`4px 4px 0`) for
  emphasis on buttons/cards — like off-registration letterpress or a travel
  poster. This is the *only* shadow.
- No soft/blurred drop shadows, no glows.

## Shapes

Crisp geometry with mid-century warmth. Mostly square corners (`rounded.none`/
`sm`); `pill` only for small stamps/badges. Signature motifs:

- **Stamp / postmark**: perforated (dashed) edges, a circular cancellation mark,
  `vermilion` ink — for presence, CEFR level, unread.
- **Par avion border**: red/blue dashed frame for correspondence cards.
- **Roundel / badge** and **halftone dots** for texture and accents.

## Paper texture

The background carries a subtle paper grain. Achieve it in CSS with no asset: an
inline **SVG `feTurbulence`** fractal-noise layer at low opacity (~3–5%)
multiplied over `paper`, plus an optional faint vignette. It must stay quiet —
felt, not seen — and never reduce text contrast below WCAG AA.

## Components

- **Button** — square-ish, `ink` fill / `paper` text, tracked caption type;
  on hover a hard `teal` block-shadow. `buttonAccent` (coral) for primary CTAs;
  `buttonSecondary` is a hairline outline.
- **Input / select** — cream field, hairline `rule` border with a deboss,
  `ochre` focus border. Labels in caption type.
- **Postcard** — the workhorse card (conversations, personas): `paperShade`
  ground, hairline frame, a postmark/stamp in one corner. Square corners.
- **Masthead / nav** — "françoise" in Fraunces at masthead scale over a rule;
  cream ground; the periodical's nameplate.
- **Stamp / badge** — Courier Prime, dashed `vermilion` edge; carries presence
  ("Sleeping · 01:14"), CEFR level, unread counts.

## Do's and Don'ts

**Do**
- Let one picture/masthead/color block be the layout; keep type tight around it.
- Keep the ground cool cream ("oyster"); use accents in confident blocks.
- Reach for the postal metaphor (stamps, postmarks, par avion) as the motif.
- Use rules, deboss, and one hard block-shadow for depth.

**Don't**
- Don't use pure white, soft drop-shadows, glows, or gradients-as-decoration.
- Don't scatter many accent colors in one view, or crowd the margins.
- Don't set body copy in Fraunces or running text in Courier Prime.
- Don't add ornament where scale and space would do the work.
