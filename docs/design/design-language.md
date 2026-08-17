# Design Language

The console is a professional instrument for people who spend hours triaging security findings. Ledger v2 keeps that job description but replaces the flat, hairline-only surface language with a warmer, more finished visual system inspired by Customer.io's product design tokens (surfaces, radius scale, shadow formula, pill controls, and its signature ink-to-flare accent pattern), translated for a dense, keyboard-first data tool rather than a marketing site.

Name of the language: **Ledger**. Still a calm, tabular surface with sharp information hierarchy, now with real elevation, a distinct brand ink, and a small "flare" accent used the way the inspiration uses it: sparingly, as a highlight, never as a wash.

## Principles

1. **Structure over decoration.** Hierarchy comes from spacing, weight, and alignment first. Elevation and color are layered on top of that structure, never used to fake it. If an element does not help someone decide what to fix next, it does not ship.
2. **Color is a signal, not a theme.** The interface is neutral; severity, status, and interactive states carry the chroma. A screen full of findings should still read as mostly neutral until the data demands attention.
3. **Density with breathing room.** Expert users want rows per screen, not cards. Compact line heights inside components, generous margins between regions.
4. **Motion explains, never performs.** 120-200 ms ease-out transitions on panels and state changes; nothing bounces, nothing floats. Respect `prefers-reduced-motion` completely.
5. **Keyboard-first.** Every workflow reachable without a mouse. The pointer is an alternative input, not the primary one.
6. **Ink and flare.** One deep, desaturated brand ink carries structure and primary actions; one bright accent (the "flare") is reserved for the single most important thing on screen: a hover ring on the primary action, a positive result, a selected row. It never spreads to backgrounds or body text.

## Color system

The palette is built from six OKLCH ramps (converted to sRGB below for implementation). `spruce` is the brand ink: a deep, desaturated teal-navy that anchors both themes. `charcoal` is the neutral gray used for surfaces and borders. `verdant`, `mustard`, `zest`, `wave`, `blush`, and `nova` are the highlight hues, each reserved for one semantic meaning so a color always means the same thing everywhere in the product.

### Brand ink and neutrals

| Token | Hex | Role |
|-------|-----|------|
| `spruce-25` | `#eff9fa` | lightest tint |
| `spruce-200` | `#a1c2c6` | dark-theme secondary text |
| `spruce-300` | `#79a1a6` | dark-theme tertiary text |
| `spruce-500` | `#437278` | secondary text (light), border-strong (dark) |
| `spruce-700` | `#0b363b` | primary accent, CTA background (light) |
| `spruce-800` | `#00262b` | CTA hover (light), surface-2 (dark) |
| `spruce-900` | `#032125` | primary text (light), surface-1 (dark) |
| `spruce-975` | `#021416` | app background (dark) |
| `charcoal-25` | `#fafafa` | app background (light) |
| `charcoal-50` | `#f5f5f5` | surface-2 (light) |
| `charcoal-100` | `#ebebeb` | surface-3 / border-subtle (light) |
| `charcoal-600` | `#5d5d5d` | tertiary text (light) |
| `charcoal-700` | `#313131` | neutral chip foreground |

### Highlight ramps (semantic hues)

| Hue | Light bg / fg | Dark bg / fg | Meaning |
|-----|----------------|---------------|---------|
| `blush` | `#ffe9f3` / `#7f0b4d` | `#230514` / `#fd95c2` | critical severity, reopened, destructive |
| `zest` | `#fdf0e9` / `#863d1c` | `#230900` / `#f29062` | high severity, in remediation |
| `mustard` | `#fff2d2` / `#83611c` | `#1b0f00` / `#edb73b` | medium severity, risk accepted |
| `verdant` | `#eafde8` / `#005911` | `#001201` / `#95ef9b` | low severity, fixed, success, the accent flare |
| `wave` | `#e2f4ff` / `#123a88` | `#000c26` / `#91c8f5` | info severity, new |
| `nova` | `#f6f4ff` / `#5923ce` | `#0f0927` / `#d2caff` | triaged |

Every pair above was checked against WCAG AA (4.5:1 minimum for the 0.6875 rem chip text; all pairs land between 5.1:1 and 13.9:1). Form-control borders are held to the separate 3:1 non-text bar (WCAG 1.4.11), since an input here is identified by its outline alone: `--field-border` measures 3.19:1 on light and 3.14:1 on dark against the surface behind it. `verdant-300` (`#abffae`) is reserved as the flare: the CTA background on dark theme and the hover/focus glow ring on primary buttons in both themes. It is never used for body text because it does not carry enough contrast on its own to be legible as text.

### Interactive tokens

| Token | Light | Dark | Role |
|-------|-------|------|------|
| `--accent` | `#0b363b` (spruce-700) | `#abffae` (verdant-300) | links, focus outline, selected-row bar |
| `--cta-bg` / `--cta-bg-hover` | `#0b363b` / `#00262b` | `#abffae` / `#95ef9b` | primary button fill |
| `--cta-fg` | `#ffffff` | `#032125` | primary button text (always high-contrast against its own fill) |
| `--flare-ring` | `#abffae` at 55% alpha | `#abffae` at 32% alpha | 4 px glow ring on primary-button hover/focus |
| `--focus-ring` | `#0b363b` at 22% alpha | `#abffae` at 24% alpha | 3 px ring on focused form controls |
| `--field-border` | `#909090` | `#437278` | input, select, and textarea outlines |
| `--danger` | `#7f0b4d` | `#fd95c2` | destructive text, error states |
| `--ok` | `#005911` | `#95ef9b` | success text |

## Typography

- **UI face**: Inter Variable (self-hosted), weights 400/500/600/700. Fallback stack: `"Inter Variable", Inter, Arial, sans-serif`, matching the fallback order of the product this is inspired by.
- **Data face**: JetBrains Mono for paths, hashes, rule keys, code. Fallback `ui-monospace, Consolas, monospace`.
- **Numerals**: `font-variant-numeric: tabular-nums` on every table, metric, and timestamp so columns align.
- Scale (rem): 0.75 caption / 0.8125 table body and controls / 0.875 body / 1 controls-large / 1.125 section titles / 1.5 page titles / 1.875 empty-state headline.
- Line heights: 1.125 for headings, 1.375 for table rows and controls, 1.55 for prose.
- Tracking: -0.02em on headings and the brand name (tighter, more finished), 0 on body, 0.04em uppercase on chips and kickers.
- Tone: editorial. Labels are lowercase-calm ("last seen", "owned by"), never SHOUTING; sentence case everywhere; no colons after labels.

## Spacing, radius, elevation

- Base unit 4 px (matches the inspiration's own spacing token); component paddings from the scale 4/8/12/16/24/32; page gutters 24-32.
- Radius scale: 2 px (`xs`, focus-ring corners) / 4 px (`sm`, `kbd`, the file-picker button, skeletons) / 6 px (`md`, buttons, inputs, selects, textareas) / 8 px (`lg`, panels, cards, inspector sections, the search field) / 12 px (`xl`, floating overlays: command palette, dialogs, login card) / 999 px (`pill`, chips, avatars, and primary/CTA buttons).
- Primary actions are pill-shaped; functional toolbar controls, inputs, and secondary buttons stay rectangular at `md`/`lg` so the dense table surface does not turn into a marketing page.
- Elevation uses a layered formula instead of a flat hairline. Three levels:
  - `--shadow-card` (panels, cards, the table, empty states): `0 0 0 1px var(--border-subtle), 0 2px 4px rgb(3 33 37 / 0.05), 0 12px 24px rgb(3 33 37 / 0.07)` on light.
  - `--shadow-raised` (the command bar, the pressed segmented control): `0 1px 2px rgb(3 33 37 / 0.07)` on light.
  - `--shadow-overlay` (command palette, dialogs, skip link, the mobile inspector): `0 0 0 1px var(--border-strong), 0 16px 40px rgb(3 33 37 / 0.18)` on light.
  Dark theme keeps the same geometry but swaps the shadow color to neutral black at higher opacity, so depth still reads on a dark ground: `0.32` / `0.36` for the card layers, `0.4` for raised, `0.55` for overlays.
- `--scrim` dims the page behind an overlay: `rgb(3 33 37 / 0.32)` on light, `rgb(2 20 22 / 0.66)` on dark, with a 2 px backdrop blur.
- The CTA flare ring (`--flare-ring`) appears only on hover/focus of a primary button: `box-shadow: 0 0 0 4px var(--flare-ring)`, layered outside the button's own shadow. Form controls use the separate, accent-tinted `--focus-ring` at 3 px so the flare stays reserved for the primary action.

## Motion

- Durations: 120 ms (hover/press), 160 ms (reveals: inspector, popover), 200 ms (workspace-level transitions).
- Easing: `cubic-bezier(0, 0, 0.2, 1)` for entrances and one-way reveals, `cubic-bezier(0.4, 0, 0.2, 1)` for reversible state changes (hover, toggle). Both are taken directly from the inspiration's own easing tokens.
- Panels slide 8 px and fade; nothing scales or bounces. Skeletons pulse at 1.6 s.
- `prefers-reduced-motion: reduce` disables all non-essential transitions in one media block at the token layer.

## Interaction states

- Hover: `--surface-3` fill on rows and ghost controls; primary buttons get the flare ring instead of a fill change.
- Focus: 2 px `--accent` outline with 2 px offset, visible only via `:focus-visible`. Form controls are the one exception: they swap their border to `--accent` and add a 3 px `--focus-ring` on plain `:focus`, because clicking into a text field should show where the caret landed and a 1 px border change alone is too weak a cue.
- Selected row: 2 px inset accent bar on the left edge + `--surface-2` fill (not a full accent wash).
- Destructive actions always require an explicit confirm step and use `--danger` only on the confirming control.

## Accessibility

- WCAG AA minimum: all fg/bg pairs above 4.5:1 (checked programmatically for every chip pair above; most exceed 6:1).
- Full keyboard operability; roving tab index in tables; `aria-live="polite"` for async result counts; semantic landmarks (`header`, `main`, `nav`); labels tied to inputs; skip-to-content link.
- Type scales with browser settings (rem-based); layout tolerates 200% zoom.

## Voice

Empty states teach ("No findings match this view. Clear a filter or upload a scan."), errors state cause and next step, and success is quiet: a row appears, a chip changes color, no confetti.
