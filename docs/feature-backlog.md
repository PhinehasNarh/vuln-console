# Feature Backlog

Everything we could build next, grouped by theme. The committed sequence lives in [roadmap.md](roadmap.md); this list is the wider menu it draws from. Items marked with a milestone are already scheduled; unmarked items are open for prioritization.

## Ingestion and coverage

- Trivy, Grype, Gitleaks, TruffleHog connectors (M2: **shipped**, with secret redaction at parse time)
- CycloneDX/Syft and SPDX SBOM import into the inventory context (M2, remaining)
- Native connectors where richer than SARIF: CodeQL, Snyk, SonarQube, OWASP Dependency-Check
- GitHub Security Alerts and GitLab Security Reports webhook ingestion (M5)
- Jenkins and Azure DevOps pipeline ingestion
- DefectDojo and Dependency-Track import (migration path for existing installs)
- Scheduled scan orchestration: trigger scanners on a cron, not just receive results
- Bulk backfill CLI: replay a directory of historical reports with original timestamps

## Intelligence and prioritization

- NVD/OSV CVE enrichment, CWE mapping, EPSS scores, CISA KEV matching (M3)
- Composite risk scoring with a documented, tunable formula (M3)
- Asset and repository criticality, internet-facing flags feeding the score (M3)
- Reachability analysis: is the vulnerable function actually called?
- Vulnerability chaining hints: findings that become critical in combination
- Exploit intelligence timeline in the inspector: PoC published, KEV added, patch released

## Triage and workflow

- False positive, risk acceptance, and exception workflows with mandatory expiry (M4)
- Ownership mapping: route findings to teams via CODEOWNERS and repo metadata (M4)
- SLA policies per severity and business unit, breach events and aging views (M3/M4)
- Saved views and shareable filter permalinks
- Bulk operations: triage fifty findings in one keyboard action
- Suppression-as-code: export accepted suppressions to scanner config files
- Discussion threads and @mentions on findings (M5+)

## Remediation

- Dependency upgrade recommendations with version conflict solving (M7)
- Automated fix pull requests for dependency bumps (M7)
- Secure code suggestions per finding class with before/after examples (M6/M7)
- Compensating control tracking with review dates
- "Fixed elsewhere" detection: same fingerprint already resolved in a sibling repo

## AI layer (M6 core, extensions after)

- Finding summaries, exploitability explanations, remediation guidance
- Natural language questions over findings ("what changed since last sprint?")
- Duplicate and cluster suggestions where fingerprints disagree but semantics match
- Scanner disagreement explanations (why tool A flags what tool B ignores)
- Executive summary generation for the management dashboard
- Local-only mode via Ollama for air-gapped installs

## Dashboards and reporting

- Security engineer dashboard: KEV exposure, aging, MTTR, backlog (M4)
- Developer view: my repos, my PRs, my dependency upgrades (M7)
- Management scorecards: risk posture trends, remediation velocity, per business unit (M7)
- Compliance mapping: findings to framework controls (SOC 2, ISO 27001, PCI)
- Scheduled report delivery by email

## Platform and operations

- OpenSearch-backed full text and faceted search (M2, remaining; needs the live stack)
- GraphQL API alongside REST (M7)
- OIDC SSO (Authentik/Keycloak) and MFA (M4+)
- Immutable audit log storage with verification (M4)
- Secrets management via Vault or SOPS (M8)
- Kubernetes/Helm deployment, internal TLS, OpenSearch security enabled (M8)
- Table virtualization for 100k+ findings, column customization, pinned columns
- Public API tokens with fine-grained scopes and expiry
- Multi-tenancy: isolated business units on one install

## How to promote an item

Pick from here during milestone planning, write acceptance criteria into [roadmap.md](roadmap.md), and if it changes an architectural decision, give it an ADR. Nothing gets built straight off this list.
