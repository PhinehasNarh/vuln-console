# Design Language

The console is a professional instrument for people who spend hours triaging security findings. The design language optimizes for sustained focus: quiet surfaces, precise typography, meaning carried by structure and a small semantic palette. It should read as a desktop-grade tool, closer to a code editor or a trading terminal than a marketing dashboard.

Name of the language: **Ledger**. Everything is a calm, tabular surface with sharp information hierarchy, like a well-set financial ledger for risk.

## Principles

1. **Structure over decoration.** Hierarchy comes from spacing, weight, and alignment, never from boxes-in-boxes or gradients. If an element does not help someone decide what to fix next, it does not ship.
2. **Color is a signal, not a theme.** The interface is neutral; only severity, status, and interactive states get chroma. A screen full of findings should look mostly gray until the data itself demands attention.
3. **Density with breathing room.** Expert users want rows per screen, not cards. Compact line heights inside components, generous margins between regions.
4. **Motion explains, never performs.** 120-200 ms ease-out transitions on panels and state changes; nothing bounces, nothing floats. Respect `prefers-reduced-motion` completely.
5. **Keyboard-first.** Every workflow reachable without a mouse. The pointer is an alternative input, not the primary one.

## Color system

Neutral ramp (dark theme is the primary theme; light theme mirrors it):

| Token | Dark | Light | Role |
|-------|------|-------|------|
| `--surface-0` | #0E1116 | #FAFAF8 | app background |
| `--surface-1` | #14181F | #FFFFFF | primary panels, table body |
| `--surface-2` | #1B212B | #F1F1EE | raised elements: popovers, sticky headers |
| `--surface-3` | #232B37 | #E8E8E4 | active/hover fills |
| `--border-subtle` | #262E3A | #E3E3DE | hairlines, table rules |
| `--border-strong` | #38424F | #C9C9C2 | focused inputs, panel edges |
| `--text-primary` | #E6EBF0 | #1A1D21 | body |
| `--text-secondary` | #9AA7B4 | #5A6068 | labels, metadata |
| `--text-tertiary` | #66707C | #8B9096 | hints, disabled |
| `--accent` | #6C9EF8 | #3B6FE0 | interactive elements, focus, links |

Semantic severity ramp, tuned for WCAG AA on both themes, desaturated on purpose:

| Token | Dark fg / bg | Light fg / bg | Meaning |
|-------|--------------|---------------|---------|
| `--sev-critical` | #FF9AA4 / #3D1B22 | #A61B2B / #FBE9EB | critical |
| `--sev-high` | #F5B47C / #3A2617 | #A05A19 / #FAEFE3 | high |
| `--sev-medium` | #E8D07A / #34301A | #8A7415 / #F7F2DE | medium |
| `--sev-low` | #93D7A8 / #17301F | #22743E / #E7F4EB | low |
| `--sev-info` | #8FBEE8 / #182A3B | #2D6398 / #E8F0F8 | informational |
| `--ok` | #7BD8A5 | #1E7A46 | success |
| `--warn` | #E8C468 | #8F6E0F | warning |
| `--danger` | #F58E8E | #B92C2C | destructive actions, errors |

Rules: severity chips use fg-on-bg pairs; charts and sparklines reuse the same ramp; never introduce a color outside these tokens.

## Typography

- **UI face**: Inter (self-hosted), weights 400/500/600. Fallback stack: `Inter, "Segoe UI", system-ui, sans-serif`.
- **Data face**: JetBrains Mono for paths, hashes, rule keys, code. Fallback `Consolas, monospace`.
- **Numerals**: `font-variant-numeric: tabular-nums` on every table, metric, and timestamp so columns align.
- Scale (rem): 0.75 caption / 0.8125 table body and controls / 0.875 body / 1.0 section titles / 1.25 page titles / 1.5 reserved for empty states. Line heights: 1.4 in tables, 1.55 in prose.
- Tone: editorial. Labels are lowercase-calm ("last seen", "owned by"), never SHOUTING; sentence case everywhere; no colons after labels.

## Spacing, radius, elevation

- Base unit 4 px; component paddings from the scale 4/8/12/16/24/32; page gutters 24-32.
- Radius: 6 px controls, 8 px panels, 999 px chips. Nothing larger.
- Elevation: two levels only. Level 1: `0 1px 2px rgb(0 0 0 / 0.3)` on sticky headers; level 2: `0 8px 24px rgb(0 0 0 / 0.4)` on popovers/palette. No decorative shadows on static content.

## Motion

- Durations: 120 ms (hover/press), 160 ms (reveals: inspector, popover), 200 ms (workspace-level transitions). Easing `cubic-bezier(0.2, 0, 0, 1)` (fast out, settle in).
- Panels slide 8 px and fade; nothing scales or bounces. Skeletons pulse at 1.6 s.
- `prefers-reduced-motion: reduce` disables all non-essential transitions in one media block at the token layer.

## Interaction states

- Hover: `--surface-3` fill, no color shift on text.
- Focus: 2 px `--accent` ring with 2 px offset, visible only via `:focus-visible`.
- Selected row: 2 px inset accent bar on the left edge + `--surface-2` fill (not a full accent wash).
- Destructive actions always require an explicit confirm step and use `--danger` only on the confirming control.

## Accessibility

- WCAG AA minimum: all fg/bg pairs above 4.5:1 (3:1 for large text and chips with 600 weight).
- Full keyboard operability; roving tab index in tables; `aria-live="polite"` for async result counts; semantic landmarks (`header`, `main`, `nav`); labels tied to inputs; skip-to-content link.
- Type scales with browser settings (rem-based); layout tolerates 200% zoom.

## Voice

Empty states teach ("No findings match this view. Clear a filter or upload a scan."), errors state cause and next step, and success is quiet (a row appears; no confetti).
