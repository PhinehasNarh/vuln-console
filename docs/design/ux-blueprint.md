# UX Blueprint

Companion to [design-language.md](design-language.md). Defines who the product serves, the journeys that matter, and the interaction architecture the frontend implements.

## Personas

1. **Sana, staff security engineer.** Lives in the console 3+ hours a day. Cares about: what became exploitable since yesterday, SLA breaches, noisy scanners. Wants keyboard-only triage and dense tables. Success: time-to-decision per finding under 30 seconds.
2. **Marco, backend developer.** Visits weekly when a finding lands on his repo. Cares about: exactly what to change, where, and proof it matters. Wants zero security jargon detours. Success: from notification to opened fix PR without asking Sana anything.
3. **Priya, engineering manager.** Monthly. Cares about: risk trend, SLA posture, where to spend headcount. Wants three numbers and a trustworthy trend, not fifty charts. Success: board-ready posture summary in five minutes.

## Core journeys

1. **Morning triage (Sana)**: open console -> findings workspace already filtered to her saved view (new + critical/high) -> j/k through rows, inspector updates live -> disposition each via keyboard -> zero-mouse session. (Dispositions land in M4; navigation and inspection ship now.)
2. **Ingest and verify (Sana)**: Ctrl+K -> "upload report" -> drop SARIF -> toast-free quiet confirmation -> new rows appear in place with "new" status; re-upload changes nothing (dedup is visible proof of trust).
3. **Fix my finding (Marco)**: deep link from Slack/ticket (M5) -> inspector open on his finding -> location, evidence, remediation guidance -> done.
4. **Posture check (Priya)**: reporting workspace (M4+) -> KPI row + trend + SLA breaches table. Nothing else.

## Interaction architecture

The application is a **workspace shell**, not a page router:

- **Command bar** (top, slim): product mark, global search, ingest action, theme toggle, account. No sidebar in M1; workspace switcher (Findings / Scans / Reports) docks into the bar as workspaces arrive.
- **Findings workspace**: a full-height virtualizable table (the primary surface) plus a **right inspector panel** that opens on selection. Split view, resizable later; no detail-page navigation, context is never lost.
- **Command palette** (Ctrl+K or Cmd+K): fuzzy actions: focus search, apply severity presets, clear filters, upload, theme, sign out. The palette is the API of the UI; every new feature registers an action here first.
- **Progressive disclosure**: table row -> inspector -> (M2+) raw findings and evidence accordion inside the inspector. Never more than one level of hidden depth.

## Keyboard map (M1)

| Key | Action |
|-----|--------|
| `/` | focus search |
| `Ctrl/Cmd+K` | command palette |
| `j` / `ArrowDown` | next row |
| `k` / `ArrowUp` | previous row |
| `Enter` | open inspector on focused row |
| `Escape` | close inspector / palette |

## Component inventory (M1 implementation)

| Component | Notes |
|-----------|-------|
| `CommandBar` | slim 48 px bar; search input with `/` hint; quiet ingest button |
| `FindingsTable` | sticky header, keyboard roving selection, skeleton rows, aria-live count, severity chips, tabular numerals |
| `Inspector` | 380 px right panel, 160 ms slide+fade, metadata grid, source scans list, Esc/`x` to close |
| `UploadSheet` | inline sheet under the command bar; file + repository; problem-details errors verbatim |
| `CommandPalette` | level-2 elevation, fuzzy filter, arrow/enter navigation |
| `Login` | centered card on `--surface-0`, no marketing chrome |
| `SeverityChip` | fg/bg token pairs; 600 weight; uppercase 0.68 rem |

## Responsive behavior

Desktop-first: designed at 1440 wide, comfortable to 4K (content max-width 1680, table stretches, inspector fixed width). Below 1024: inspector overlays instead of splitting. Mobile is read-only triage review; deferred until M4 dashboards.

## Deferred design workstreams (tracked, not forgotten)

Virtualized rows (needed at 10k+ rows, M2 when OpenSearch search lands), saved views, bulk operations, grouped rows, drag-to-resize panels, Storybook + visual regression, illustration set, full light-theme QA pass, dependency graph and exploit timeline in the inspector (M3 data), discussion threads (M5).
