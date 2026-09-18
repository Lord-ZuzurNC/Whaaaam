---
name: Whaaaam
description: A mod-list compatibility checker whose interface stays quiet so one verdict can be loud.
colors:
  bg: "#1e1e2e"
  surface: "#313244"
  line: "#45475a"
  border: "#7f849c"
  text: "#cdd6f4"
  subtext: "#a6adc8"
  accent: "#89b4fa"
  accent-hover: "#9ec2fb"
  on-accent: "#1e1e2e"
  visited: "#cba6f7"
  good: "#a6e3a1"
  good-tint: "#3d4b48"
  warn: "#f9e2af"
  warn-tint: "#575150"
  bad: "#f38ba8"
  bad-tint: "#7c4e64"
typography:
  display:
    fontFamily: "Press Start 2P, ui-monospace, monospace"
    fontSize: "clamp(1.15rem, 0.7rem + 2.6vw, 2rem)"
    fontWeight: 400
    lineHeight: 1.1
  verdict:
    fontFamily: "Segoe UI, system-ui, -apple-system, Helvetica Neue, Arial, sans-serif"
    fontSize: "clamp(1.05rem, 0.9rem + 0.9vw, 1.35rem)"
    fontWeight: 600
    lineHeight: 1.35
    fontFeature: "tabular-nums"
  body:
    fontFamily: "Segoe UI, system-ui, -apple-system, Helvetica Neue, Arial, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.55
  figure:
    fontFamily: "Segoe UI, system-ui, -apple-system, Helvetica Neue, Arial, sans-serif"
    fontSize: "clamp(1.6rem, 1.1rem + 3.2vw, 2.75rem)"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.01em"
    fontFeature: "tabular-nums"
  label:
    fontFamily: "Segoe UI, system-ui, -apple-system, Helvetica Neue, Arial, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 600
    letterSpacing: "0.06em"
rounded:
  sm: "6px"
  md: "8px"
  pill: "20px"
spacing:
  gutter: "clamp(1rem, 4vw, 2rem)"
  shell: "72rem"
  reading: "46rem"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
    rounded: "{rounded.md}"
    padding: "0.6rem 1.2rem"
    height: "44px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
    textColor: "{colors.on-accent}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.md}"
    padding: "0.6rem 1.2rem"
    height: "44px"
  input-textarea:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.md}"
    padding: "0.8rem"
  verdict-good:
    backgroundColor: "{colors.good-tint}"
    textColor: "{colors.text}"
    typography: "{typography.verdict}"
    rounded: "{rounded.md}"
    padding: "0.9rem 1.1rem"
  verdict-warn:
    backgroundColor: "{colors.warn-tint}"
    textColor: "{colors.text}"
    typography: "{typography.verdict}"
    rounded: "{rounded.md}"
    padding: "0.9rem 1.1rem"
  verdict-bad:
    backgroundColor: "{colors.bad-tint}"
    textColor: "{colors.text}"
    typography: "{typography.verdict}"
    rounded: "{rounded.md}"
    padding: "0.9rem 1.1rem"
  table-header:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.subtext}"
    typography: "{typography.label}"
    padding: "0.75rem 0.9rem"
---

# Design System: Whaaaam

## Overview

**Creative North Star: "The Server Console"**

Whaaaam is read by a server administrator who is mid-decision and mildly annoyed. They have a mod list, they changed something, and they need one fact before they can move: which Minecraft version and loader does the whole list agree on? The interface answers that and then gets out of the way. It is a readout, not a destination.

Everything in the system is arranged to make one element loud. Surfaces are quiet tonal steps of the same palette; the header is a plain band; table headers are lowercase-weight labels rather than coloured bars. Against that flatness, the verdict banner — a tinted panel carrying a full sentence in the largest non-wordmark type on the page — is unmistakable from across a desk. That contrast is the whole design. Any change that adds a second loud thing has broken it.

Colour comes from Catppuccin, and all four palettes (Latte, Frappé, Macchiato, Mocha) are first-class: the same token names resolve to different values under `[data-theme]` on `<html>`. Mocha is the default. The palettes are a binding brand commitment, not a preference — no fifth theme, no competing palette. Every foreground/background pair in the system has been checked against WCAG AA in all four.

**Key Characteristics:**
- One accent colour, spent on exactly two elements
- Tonal layering instead of shadows; depth is a lightness step, not a glow
- The verdict is the only element permitted to raise its voice
- Four themes, one token vocabulary, zero hard-coded colours
- Pixel type is the wordmark and nothing else

## Colors

Catppuccin, applied as roles rather than swatches. Every component reads a token; a raw hex in a component rule is a defect.

### Primary
- **Catppuccin Blue** (`{colors.accent}` — Mocha `#89b4fa`, Latte `#1e66f5`, Frappé `#8caaee`, Macchiato `#8aadf4`): the identity colour. It appears on the wordmark and the Check compatibility button, and as the underline under links, the caret, the text-selection fill, and the focus ring. It is never a background for a region.
- **Accent Ink** (`{colors.on-accent}`): the only foreground permitted on an accent fill. On dark themes it is the theme's own background colour; on Latte it is pure white, because Latte's blue is too light to carry its own base.

### Secondary
- **Catppuccin Mauve** (`{colors.visited}`): visited links only. Deliberately the one hue outside the blue/neutral axis in the app body, because a visited mod link is genuinely different information.

### Tertiary
- **Verdict Green / Yellow / Red** (`{colors.good}` / `{colors.warn}` / `{colors.bad}`): status for the compatibility banner, and nothing else. They never appear as decoration, and they are always paired with their `-tint` partner as a background so the text can stay `{colors.text}`.

### Neutral
- **Canvas** (`{colors.bg}`): the page.
- **Surface** (`{colors.surface}`): the header, the footer, the table, inputs, secondary buttons. One step up from the canvas, and the only elevation move in the system.
- **Line** (`{colors.line}`): decorative separators — table rows, the header rule, container edges.
- **Border** (`{colors.border}`): interactive control edges only. It is a lighter value than Line specifically so it clears 3:1 against both the canvas and Surface; the two are not interchangeable.
- **Text / Subtext** (`{colors.text}` / `{colors.subtext}`): primary copy and metadata. Subtext is rated against both the canvas and Surface in every palette — Frappé uses Catppuccin's `subtext1` rather than `subtext0` precisely so it clears AA on a raised surface like the rest of them.

### Named Rules

**The Large Wordmark Rule.** The wordmark floor is 1.5rem, not a smaller
clamp minimum, and the reason is contrast rather than taste. It carries
`{colors.accent}` on `--surface`, where Latte's blue measures 4.04:1 — fine
against WCAG's 3:1 large-text threshold at 24px/400, and a failure against the
4.5:1 small-text one below it. Shrinking the wordmark silently breaks AA on
Latte. Measure the accent against `--surface`, never `--bg`: the header is a
raised surface, and that mistake once shipped a palette deviation that bought
0.2 and still failed.

**The One Accent Rule.** Blue appears on the wordmark and the primary action. That is the entire list. Headers, table headings, secondary buttons, and containers are Surface with a Line edge. Rarity is what makes the check action findable in a page of neutral controls — spend the accent on a fourth thing and you have spent the affordance.

**The Words-First Rule.** Status is carried by the sentence, then reinforced by colour. The verdict says "All your mods are compatible with Fabric 1.20.1" or "Most of your mods share: Fabric 1.20.1 (8/10)"; the tint and border agree with it. Colour is never the only carrier of a state, and text on a status surface is always `{colors.text}` — never the status hue itself, which fails on the light palette.

**The No-Raw-Hex Rule.** Components read tokens. The only hex values in the stylesheet are inside the four `[data-theme]` blocks and the four theme-swatch fills in the switcher, which must show the literal palette colours to do their job.

## Typography

**Display Font:** Press Start 2P (with `ui-monospace, monospace`)
**Body Font:** Segoe UI (with `system-ui, -apple-system, Helvetica Neue, Arial, sans-serif`)

**Character:** A pixel wordmark over a plain system UI face. The pixel font is the one piece of Minecraft heritage that survived into the app body, and it earns its place by appearing exactly once. Everything else is the reader's own system font, set at comfortable sizes — this is a tool someone uses in a hurry, and unfamiliar type costs them time.

### Hierarchy
- **Display** (400, `clamp(1.15rem, 0.7rem + 2.6vw, 2rem)`, 1.1): the wordmark. The only Press Start 2P on the page.
- **Verdict** (600, `clamp(1.05rem, 0.9rem + 0.9vw, 1.35rem)`, 1.35, tabular-nums, balanced): the compatibility answer. Larger than body, balanced so it never breaks to a one-word last line, and tabular so the `(8/10)` count doesn't shimmer between renders.
- **Body** (400, 1rem, 1.55): table cells, placeholder copy, version lists. Reading blocks are capped at 48ch.
- **Label** (600, 0.8125rem, 0.06em tracking, uppercase for table headings): field labels, filter labels, table headings, metadata, failure reasons.

### Named Rules

**The Wordmark-Only Rule.** Press Start 2P is loaded for one element. It is not available for headings, buttons, loading text, or the footer — a pixel face at small sizes is slow to read and the tool's users are not browsing. If a second element ever needs it, that is a signal to drop the font, not to spread it.

**The Tabular Rule.** Anything containing a version number or a count is `font-variant-numeric: tabular-nums` — the verdict, the version list, the filter note, the disclosure summary. Minecraft versions are the data; they should line up.

## Layout

A single centred column, no grid. Two width tokens do the work: `{spacing.shell}` (72rem) for the results region and filter bar, and `{spacing.reading}` (46rem) for the input block, which is narrower because it is something you read and type into rather than scan. Both use `width: min(100% - (2 * gutter), <max>)`, so the gutter is honoured before the cap and no element ever touches the viewport edge.

`{spacing.gutter}` is `clamp(1rem, 4vw, 2rem)` — one fluid value used for page padding, header padding, and the theme switcher's inset, so the left edge of the wordmark and the right edge of the switcher track together at every width.

Vertical rhythm is loose: 2rem above the input block, 1.5rem between sections, 1rem between results elements. The page is short by design; density is not a goal.

**Responsive behaviour** uses two breakpoints, both content-driven rather than device-named:
- **900px** — the filter bar stops being a single justified row and stacks its filter group above its export group.
- **640px** — the header becomes a column with the theme switcher below the wordmark (it is absolutely positioned above this width and would otherwise collide), the input actions go full-width, and the footer stacks.

The results table is always inside a horizontally scrollable, focusable region. It is never allowed to force the page itself to scroll sideways.

### Named Rules

**The No-Sideways-Page Rule.** Wide content scrolls inside its own container, with `tabindex="0"` and a `role="region"` label so keyboard users can reach it. The document never scrolls horizontally at any width.

## Elevation & Depth

There are no shadows in this system, with one exception. Depth is tonal: `{colors.bg}` is the floor, `{colors.surface}` is everything raised off it, and a 1px `{colors.line}` edge draws the boundary. Two tonal steps is the entire vocabulary — there is no third level, and nested raised surfaces are not a pattern here.

### Shadow Vocabulary
- **Container lift** (`box-shadow: 0 1px 3px var(--shadow)`): the results table only. A single-pixel offset with a soft 3px blur, in a theme-aware translucent ink — just enough to separate a long table from the canvas when the page scrolls. `--shadow` is tinted from the palette's own text colour on Latte and plain black on the dark themes.

### Named Rules

**The Two-Step Rule.** Canvas, then Surface. Anything that needs to read as "on top of" something else gets the Surface token and a Line border, not a shadow and not a third grey. If two raised things need distinguishing, use space, not elevation.

## Shapes

Softly rounded rectangles throughout: `{rounded.md}` (8px) for the things you act on and read in — buttons, the textarea, the verdict banner, the table container — and `{rounded.sm}` (6px) for smaller inset elements like selects, status messages, and footer icon targets. The only fully round forms are the theme swatches and the loading spinner, where roundness is the meaning rather than a style.

Borders are 1px everywhere. There is no thick accent bar, no coloured left rule above a hairline, and no hard offset shadow. The status banner is bordered on all four sides in its status colour at 1px — a single edge weight is what keeps a page of stacked panels from looking like a stack of tabs.

## Components

### Buttons
- **Shape:** 8px radius (`{rounded.md}`), 44px minimum height so every button is a legal touch target.
- **Primary:** accent fill, `{colors.on-accent}` label, 600 weight. Exactly one per screen — Check compatibility.
- **Secondary:** Surface fill, Text label, 1px Border edge, 500 weight. Both exports.
- **Hover:** primary shifts to `{colors.accent-hover}`; secondary keeps its fill and moves its border to the accent. Both are 0.2s.
- **Focus:** a 2px accent outline at 2px offset, from the global `:focus-visible` rule. Buttons never remove it.
- **Disabled:** 0.6 opacity with `cursor: progress`, used while a check is in flight.

### Inputs / Fields
- **Style:** Surface fill, 1px Border edge, 8px radius, body type at 1.6 line-height. Always paired with a visible `<label>`; a placeholder is an example, never a label.
- **Focus:** accent outline plus an accent border, so the field reads as active from both the ring and its own edge.
- **Hint:** a `.label-hint` span inside the label, Subtext, normal weight, on its own line.
- **Selects:** 44px minimum height, 6px radius, Label-sized type.

### Cards / Containers
- **Corner Style:** 8px radius.
- **Background:** Surface.
- **Border:** 1px Line.
- **Shadow Strategy:** none, except the results table's container lift.
- **Internal Padding:** 0.75–1.1rem.

### Data Table
- **Headings:** Surface background, Subtext colour, Label type uppercase with 0.06em tracking, and a 1px Border bottom rule — the heavier bottom edge is what separates the head from the body, not a fill.
- **Rows:** 1px Line separators, dropped on the last row. Cells are top-aligned, because the versions cell can be tall.
- **Failed rows:** carry a drawn alert icon (circle and exclamation, 20px, the provider marks' size) in the source column in `{colors.bad}`, and the failure reason as Label-sized Subtext in place of versions. The icon is a graphic, so the status hue is legal there (3:1 non-text; lowest is Frappé at 3.57:1) where it would not be as type; it is `aria-hidden`, and a visually-hidden "Could not be checked" carries the state. A failed URL shown as the name breaks at its slashes, not mid-word. They stay in the table. A mod that could not be checked is an unanswered question, never a silent omission.
- **Versions cell:** a native `<details>`/`<summary>` disclosure labelled with the count ("14 versions"), which supplies its own expanded state, keyboard handling, and `aria-expanded`.

### Verdict Banner
The signature component, and the largest type on the page — the version+loader
figure is set at `{typography.figure}`, a step above the wordmark, because the
answer outranks the brand. The figure is emphasised *inside* the sentence rather
than repeated above it, so the wording PRODUCT.md records ships unchanged. The
banner is focusable (`tabindex="-1"`) and receives focus when a check finishes,
which scrolls the answer into view and reads it out in one move — there is no
second live region duplicating it. Full width of the results column, tinted background, 1px status border, verdict type, centred and balanced. Three states: `good` (whole list agrees), `warning` (partial consensus, or consensus with unchecked mods), `bad` (no consensus, or nothing could be checked). Text is always `{colors.text}` regardless of state.

### Theme Switcher
Four 24px circles in a pill, each filled with that palette's literal base colour, inside a `radiogroup` with roving tabindex. The checked swatch takes an accent ring; a sliding `{colors.line}` pill tracks behind it. Absolutely positioned to the header's right edge above 640px, static below it.

### Navigation
There is none. The product is one screen, and adding a nav would imply there is somewhere else to go.

## Do's and Don'ts

### Do:
- **Do** read colour from tokens. Every value resolves through `[data-theme]`; the four theme blocks are the only place hex belongs.
- **Do** check new foreground/background pairs against all four palettes. Latte is the one that breaks — its accents are mid-lightness, so a colour that reads fine on Mocha may fail there.
- **Do** put status in words first and colour second.
- **Do** use `{colors.border}` for anything interactive and `{colors.line}` for anything decorative. They exist as separate tokens because only one of them clears 3:1.
- **Do** give every new control a 44px minimum touch target. Under
  `pointer: coarse` the theme swatches keep their 24px circle inside a 44px hit
  area rather than growing.
- **Do** put the answer above its own substantiation: `#results` precedes
  `#filter-block`, and the filter bar stays `hidden` until there is a result.
- **Do** mark the mods that fall outside the verdict's consensus in words
  ("Not on Fabric 1.20.1"), never by colour alone.
- **Do** keep numeric content on `tabular-nums`.
- **Do** let wide content scroll inside a labelled, focusable region.

### Don't:
- **Don't** spend the accent on a third element. The wordmark and the primary action, and nothing else.
- **Don't** use a status hue as text colour. On Latte, green and yellow fail against every surface in this system.
- **Don't** add a shadow to make something look raised. Use the Surface token.
- **Don't** use Press Start 2P for anything but the wordmark.
- **Don't** introduce a fifth theme or a competing palette. Catppuccin's four are a brand commitment.
- **Don't** drop a mod from the table or the count because its lookup failed.
- **Don't** hard-code a colour in a component rule, including in the footer — it was a texture-and-brown exception once and is now fully tokenised.
