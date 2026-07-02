# The Vulnerability Console, Explained Without Jargon

A plain-language guide for managers, stakeholders, and anyone who does not live in security tooling.

## The problem

Modern software teams run many automated security scanners. Each one produces long reports in its own format, and they overlap: the same weakness gets reported five times in five shapes. Real, dangerous issues drown in duplicates and low-priority noise. Security engineers burn hours re-reading reports instead of fixing problems, and nobody can confidently answer "how exposed are we right now?"

## What this product does

The console is a single control room for all of those reports. It:

1. **Collects** results from every scanner in one place, automatically.
2. **Translates** them into one common language, so a finding is a finding regardless of which tool reported it.
3. **Removes duplicates.** Five reports about the same flaw become one entry with five pieces of supporting evidence. Uploading the same report twice changes nothing, which is how you know you can trust the numbers.
4. **Adds context** (coming in the next milestones): is this weakness actually being exploited in the wild? How critical is the system it lives in? That turns a pile of alerts into a ranked to-do list.
5. **Tracks decisions.** When someone accepts a risk or marks a false alarm, the decision has an owner, a reason, an expiry date, and a permanent audit trail.
6. **Shows the right view to the right person.** Engineers get a fast working screen; developers see only their own repositories; management gets trends and totals.

## What exists today

- The full technical blueprint (architecture, security analysis, delivery plan through eight milestones).
- A working first slice: you can sign in, upload a real scanner report, and watch it become de-duplicated findings in a polished interface, with permissions and an audit trail behind it.
- Everything runs on your own hardware; no data leaves the building.

## What it is not

It does not scan code itself; it makes the scanners you already run useful. It also never auto-dismisses anything: people make the risk decisions, the console makes those decisions cheap, visible, and reversible.

## Small glossary

| Term | Plain meaning |
|------|---------------|
| Finding | One security problem, after duplicates are merged |
| Scanner | A tool that inspects code or systems for weaknesses (Semgrep, Trivy, ...) |
| SARIF | A standard file format scanners use to report results |
| CVE | A public ID number for a known software vulnerability |
| Severity | How bad a problem could be (critical, high, medium, low, info) |
| Triage | Deciding what to do about each finding, and in what order |
| False positive | A scanner alarm that turns out to be wrong |
| Risk acceptance | A documented, time-limited decision to live with a known issue |
| SLA | The promised deadline for fixing a problem of a given severity |
| Audit trail | The permanent record of who did what, when, and why |

## Where it goes next

In order: more scanner formats, live threat intelligence (is this being exploited right now?), triage workflows with deadlines, alerting and ticket integration (Slack, Jira), AI-assisted explanations and fix suggestions, and management dashboards. The full plan lives in [roadmap.md](roadmap.md).
