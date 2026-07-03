"""Render a ReportData into a self-contained, print-ready, branded HTML report.

Everything is inlined (styles, logo) so the file is a single shareable artifact.
All dynamic text is HTML-escaped: scanner output is untrusted input.
"""

from datetime import datetime
from html import escape

from vulnconsole.contexts.reporting.application.report import (
    ReportData,
    TimelineEvent,
)
from vulnconsole.contexts.reporting.infrastructure.logo import monogram

_SEVERITY_STYLE = {
    "critical": ("#a61b2b", "#fbe9eb"),
    "high": ("#a05a19", "#faefe3"),
    "medium": ("#8a7415", "#f7f2de"),
    "low": ("#22743e", "#e7f4eb"),
    "info": ("#2d6398", "#e8f0f8"),
}
_SLA_STYLE = {
    "overdue": ("#a61b2b", "#fbe9eb", "overdue"),
    "due_soon": ("#a05a19", "#faefe3", "due soon"),
    "on_track": ("#22743e", "#e7f4eb", "on track"),
    "none": ("#5a6068", "#f1f1ee", "no sla"),
}
_CATEGORY_COLOR = {
    "ingest": "#3b6fe0",
    "triage": "#6b46c1",
    "identity": "#5a6068",
    "security": "#a61b2b",
    "event": "#8b9096",
}


def _dt(value: datetime) -> str:
    return value.strftime("%b %d, %Y %H:%M UTC")


def _date(value: datetime) -> str:
    return value.strftime("%b %d, %Y")


def _severity_chip(severity: str) -> str:
    fg, bg = _SEVERITY_STYLE.get(severity, _SEVERITY_STYLE["info"])
    return (
        f'<span class="chip" style="color:{fg};background:{bg}">{escape(severity)}</span>'
    )


def _sla_chip(status: str) -> str:
    fg, bg, label = _SLA_STYLE.get(status, _SLA_STYLE["none"])
    return f'<span class="chip" style="color:{fg};background:{bg}">{escape(label)}</span>'


def _logo_mark(data: ReportData, logo_uri: str | None) -> str:
    if logo_uri:
        return f'<img class="logo" src="{escape(logo_uri, quote=True)}" alt="logo" />'
    return f'<span class="logo monogram">{escape(monogram(data.company_name))}</span>'


def _summary_tiles(data: ReportData) -> str:
    s = data.summary
    tiles = [
        ("findings in period", s.total_findings, ""),
        ("overdue", s.overdue, "danger" if s.overdue else ""),
        ("assigned", s.assigned, ""),
        ("unassigned", s.unassigned, "warn" if s.unassigned else ""),
        ("repositories", s.repositories, ""),
    ]
    cells = "".join(
        f'<div class="tile {cls}"><div class="tile-num">{value}</div>'
        f'<div class="tile-label">{escape(label)}</div></div>'
        for label, value, cls in tiles
    )
    return f'<div class="tiles">{cells}</div>'


def _severity_bar(data: ReportData) -> str:
    total = max(data.summary.total_findings, 1)
    segments = []
    legend = []
    for sev in ("critical", "high", "medium", "low", "info"):
        count = data.summary.by_severity.get(sev, 0)
        if count == 0:
            continue
        pct = count / total * 100
        fg, _bg = _SEVERITY_STYLE[sev]
        segments.append(f'<span style="width:{pct:.1f}%;background:{fg}"></span>')
        legend.append(
            f'<span class="legend-item"><span class="dot" style="background:{fg}"></span>'
            f"{escape(sev)} {count}</span>"
        )
    if not segments:
        return ""
    return (
        f'<div class="sev-bar">{"".join(segments)}</div>'
        f'<div class="legend">{"".join(legend)}</div>'
    )


def _findings_rows(data: ReportData) -> str:
    if not data.findings:
        return '<tr><td colspan="6" class="empty">No findings in this period.</td></tr>'
    rows = []
    for f in data.findings:
        rows.append(
            "<tr>"
            f"<td>{_severity_chip(f.severity)}</td>"
            f'<td class="title"><div>{escape(f.title)}</div>'
            f'<div class="rule">{escape(f.rule_key)}</div></td>'
            f"<td>{escape(f.repository)}</td>"
            f"<td>{escape(f.owner or 'unassigned')}</td>"
            f"<td>{_sla_chip(f.sla_status)}</td>"
            f'<td class="nums">{_date(f.first_seen)}</td>'
            "</tr>"
        )
    return "".join(rows)


def _timeline_items(events: list[TimelineEvent]) -> str:
    if not events:
        return '<p class="empty">No recorded activity in this period.</p>'
    items = []
    for event in events:
        color = _CATEGORY_COLOR.get(event.category, _CATEGORY_COLOR["event"])
        items.append(
            '<li class="tl-item">'
            f'<span class="tl-dot" style="background:{color}"></span>'
            '<div class="tl-body">'
            f'<div class="tl-time nums">{_dt(event.at)}</div>'
            f'<div class="tl-summary">{escape(event.summary)}</div>'
            f'<div class="tl-actor">{escape(event.actor)}</div>'
            "</div></li>"
        )
    return f'<ul class="timeline">{"".join(items)}</ul>'


def render_html(data: ReportData, logo_uri: str | None) -> str:
    company = escape(data.company_name)
    label = escape(data.confidential_label)
    period = f"{_date(data.since)} to {_date(data.until)}"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{company} security audit report</title>
<style>
  :root {{
    --ink: #1a1d21; --muted: #5a6068; --faint: #8b9096;
    --line: #e3e3de; --panel: #ffffff; --bg: #f4f4f1; --accent: #3b6fe0;
    --danger: #a61b2b; --warn: #8a7415;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; background: var(--bg); }}
  body {{
    font-family: "Segoe UI", system-ui, -apple-system, Helvetica, Arial, sans-serif;
    color: var(--ink); font-size: 13px; line-height: 1.55;
    -webkit-print-color-adjust: exact; print-color-adjust: exact;
  }}
  .nums {{ font-variant-numeric: tabular-nums; }}
  .page {{
    max-width: 900px; margin: 24px auto; background: var(--panel);
    border: 1px solid var(--line); border-radius: 10px; padding: 44px 48px;
    box-shadow: 0 8px 30px rgb(20 20 20 / 0.06); position: relative; overflow: hidden;
  }}
  .watermark {{
    position: fixed; top: 42%; left: -6%; width: 120%; text-align: center;
    font-size: 92px; font-weight: 800; letter-spacing: 0.1em;
    color: rgba(166,27,43,0.05); transform: rotate(-24deg);
    pointer-events: none; z-index: 0; white-space: nowrap;
  }}
  .content {{ position: relative; z-index: 1; }}
  header.cover {{
    display: flex; align-items: flex-start; justify-content: space-between;
    gap: 20px; padding-bottom: 20px; border-bottom: 2px solid var(--ink);
  }}
  .brand {{ display: flex; align-items: center; gap: 16px; }}
  .logo {{ height: 52px; width: auto; max-width: 180px; border-radius: 8px; }}
  .logo.monogram {{
    display: inline-flex; align-items: center; justify-content: center;
    height: 52px; width: 52px; background: var(--ink); color: #fff;
    font-weight: 700; font-size: 20px; letter-spacing: 0.04em;
  }}
  .titles h1 {{ margin: 0; font-size: 20px; letter-spacing: -0.01em; }}
  .titles .company {{ color: var(--muted); font-size: 13px; margin-top: 2px; }}
  .confidential {{
    border: 1.5px solid var(--danger); color: var(--danger);
    font-weight: 700; font-size: 11px; letter-spacing: 0.14em;
    padding: 5px 10px; border-radius: 6px; white-space: nowrap;
  }}
  .metabar {{
    display: flex; flex-wrap: wrap; gap: 28px; margin: 18px 0 6px;
    color: var(--muted); font-size: 12px;
  }}
  .metabar b {{ color: var(--ink); font-weight: 600; }}
  h2.section {{
    font-size: 12px; text-transform: uppercase; letter-spacing: 0.1em;
    color: var(--faint); margin: 34px 0 12px; padding-bottom: 6px;
    border-bottom: 1px solid var(--line);
  }}
  .tiles {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; }}
  .tile {{ border: 1px solid var(--line); border-radius: 8px; padding: 14px; }}
  .tile-num {{ font-size: 26px; font-weight: 700; font-variant-numeric: tabular-nums; }}
  .tile-label {{ color: var(--muted); font-size: 11px; text-transform: uppercase;
    letter-spacing: 0.06em; }}
  .tile.danger .tile-num {{ color: var(--danger); }}
  .tile.warn .tile-num {{ color: var(--warn); }}
  .sev-bar {{
    display: flex; height: 10px; border-radius: 999px; overflow: hidden;
    margin: 16px 0 10px; background: var(--line);
  }}
  .sev-bar span {{ display: block; height: 100%; }}
  .legend {{ display: flex; flex-wrap: wrap; gap: 16px; color: var(--muted); font-size: 12px; }}
  .legend-item {{ display: inline-flex; align-items: center; gap: 6px; }}
  .dot {{ width: 9px; height: 9px; border-radius: 999px; display: inline-block; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
  th {{ text-align: left; color: var(--faint); font-weight: 600; padding: 8px 10px;
    border-bottom: 1px solid var(--line); }}
  td {{ padding: 9px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }}
  td.title div:first-child {{ font-weight: 500; }}
  td.title .rule {{ color: var(--faint); font-size: 11px; font-family: Consolas, monospace; }}
  .chip {{
    display: inline-block; padding: 2px 8px; border-radius: 999px;
    font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em;
  }}
  .empty {{ color: var(--muted); padding: 16px 10px; }}
  .timeline {{ list-style: none; margin: 0; padding: 0 0 0 4px; }}
  .tl-item {{ position: relative; padding: 0 0 18px 26px; border-left: 2px solid var(--line); }}
  .tl-item:last-child {{ border-left-color: transparent; padding-bottom: 0; }}
  .tl-dot {{ position: absolute; left: -7px; top: 2px; width: 12px; height: 12px;
    border-radius: 999px; border: 2px solid var(--panel); }}
  .tl-time {{ color: var(--faint); font-size: 11px; }}
  .tl-summary {{ font-weight: 500; }}
  .tl-actor {{ color: var(--muted); font-size: 11px; }}
  footer.note {{
    margin-top: 34px; padding-top: 14px; border-top: 1px solid var(--line);
    color: var(--faint); font-size: 11px; display: flex; justify-content: space-between; gap: 16px;
  }}
  @page {{ size: A4; margin: 14mm; }}
  @media print {{
    html, body {{ background: #fff; }}
    .page {{ margin: 0; border: none; border-radius: 0; box-shadow: none;
      padding: 0; max-width: none; }}
    h2.section {{ break-after: avoid; }}
    tr, .tl-item {{ break-inside: avoid; }}
  }}
</style>
</head>
<body>
  <div class="watermark">{label}</div>
  <div class="page"><div class="content">
    <header class="cover">
      <div class="brand">
        {_logo_mark(data, logo_uri)}
        <div class="titles">
          <h1>Security Audit Report</h1>
          <div class="company">{company}</div>
        </div>
      </div>
      <div class="confidential">{label}</div>
    </header>

    <div class="metabar">
      <span>Reporting period<br /><b>{escape(period)}</b></span>
      <span>Generated by<br /><b>{escape(data.generated_by)}</b></span>
      <span>Generated at<br /><b class="nums">{_dt(data.generated_at)}</b></span>
    </div>

    <h2 class="section">Executive summary</h2>
    {_summary_tiles(data)}
    {_severity_bar(data)}

    <h2 class="section">Findings in period</h2>
    <table>
      <thead><tr>
        <th>severity</th><th>finding</th><th>repository</th>
        <th>owner</th><th>sla</th><th>first seen</th>
      </tr></thead>
      <tbody>{_findings_rows(data)}</tbody>
    </table>

    <h2 class="section">Incident timeline</h2>
    {_timeline_items(data.timeline)}

    <footer class="note">
      <span>{label} &middot; Prepared for {company}. Distribution restricted.</span>
      <span>Generated by {escape(data.generated_by)}</span>
    </footer>
  </div></div>
</body>
</html>"""
