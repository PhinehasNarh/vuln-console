# Roadmap

Milestones are vertical slices: each one ships working, tested, documented capability plus the compose/CI updates to run it. Refactor before expanding; no milestone starts until the previous one's acceptance criteria pass.

## M0: Architecture and scaffold (this milestone)

**Scope**: architecture package (overview, domain model, decomposition, 12 ADRs, threat model, API conventions, roadmap), monorepo scaffold, infrastructure-only Docker Compose stack, CI stub.

**Acceptance criteria**

- `docker compose up -d` brings up all 8 infrastructure services healthy
- All documents cross-link and diagrams render
- CI stub runs (typography check, compose validation, backend lint)

## M1: Walking skeleton

**Scope**: the thinnest end-to-end slice. Upload a Semgrep SARIF file, watch it become findings in a UI.

- Ingestion: `POST /api/v1/scans` (multipart upload), SARIF connector, artifact to MinIO, Scan lifecycle
- Normalization: fingerprint v1, canonical Finding persistence
- API: findings list/detail with pagination, filtering by severity/repository/scanner
- Worker: first NATS consumer chain (received, parsed, normalized); worker framework decision (nats-py vs FastStream) recorded as ADR-0013
- Identity: user login, JWT issue/refresh, one API token flow, roles seeded, AuditEvent on every mutation
- Frontend: Vite scaffold, login, findings table, finding detail
- Compose: api, worker, frontend containers join the stack behind Traefik
- Tests: unit + API integration (testcontainers), CI activates fully
- Sample data: example SARIF artifacts under `deploy/sample-data/`

**Acceptance criteria**

- Fresh clone to running stack in under 10 minutes following the README
- Uploading the sample SARIF twice produces zero duplicate findings
- Unauthenticated requests rejected; viewer role cannot mutate
- All mutations visible in the audit log

## M2: Connector expansion and correlation

**Scope**: Trivy, Grype, Gitleaks, CycloneDX/Syft, SPDX, TruffleHog connectors; fingerprint v2 (class-specific location keys); cross-scanner correlation; duplicate review UI; secret evidence encryption + RBAC gate; parser hardening (fuzz corpus, size/depth limits); OpenSearch projection + search API.

**Acceptance criteria**: same vulnerability reported by Trivy and Grype yields one finding with two raw findings; secret values never appear in API responses without the reveal permission; malformed artifacts fail safely with actionable errors.

## M3: Enrichment and risk

**Scope**: NVD/OSV, EPSS, KEV feed sync (scheduled jobs); vulnerability entity; composite risk scoring with documented formula; SLA policies, due dates, breach events; asset/repository criticality inputs.

**Acceptance criteria**: findings carry EPSS/KEV within one sync cycle; risk ordering demonstrably differs from raw CVSS ordering; SLA breach emits an event.

## M4: Triage workflows and dashboards

**Scope**: full lifecycle transitions with justification; false positive, risk acceptance, and exception workflows with mandatory expiry and automatic reopen; ownership mapping; full RBAC matrix; security engineer dashboard (KEV exposure, aging, MTTR, backlog); immutable audit storage.

**Acceptance criteria**: expiry reopens findings without human action; every workflow action requires and records justification; dashboard numbers reconcile with API queries.

## M5: Automation and integrations

**Scope**: webhook ingestion (GitHub/GitLab security events); Jira + GitHub Issues ticket creation with backlinks; Slack/Teams/email notifications with routing rules; scheduled scan orchestration hooks; notification preferences.

**Acceptance criteria**: SLA breach opens a ticket and posts to Slack within one minute; ticket state syncs back to finding.

## M6: AI layer

**Scope**: `LLMProvider` abstraction, Anthropic + Ollama adapters (consult the `claude-api` skill for current models/APIs); finding summaries; exploitability explanations; remediation guidance with secure code examples; NL Q&A over findings; duplicate/cluster suggestions; prompt redaction layer; per-capability provider routing.

**Acceptance criteria**: AI output is advisory and schema-validated; redaction provably strips secret values (tested); local-only mode works end to end.

## M7: Remediation automation and second API

**Scope**: dependency upgrade recommendations with version solving; fix PR generation for dependency bumps; compensating control tracking; suppression management; GraphQL API (Strawberry); developer and management dashboards; executive summary generation.

**Acceptance criteria**: a fix PR opens against a sample repository with passing description and diff; GraphQL serves the findings graph with authz parity to REST.

## M8: Hardening and portability

**Scope**: performance/load testing and remediation of hot paths; Kubernetes manifests or Helm chart; secrets management (Vault or SOPS); OpenSearch security enabled; internal TLS; backup/restore runbooks; operator guide; production deployment guide.

**Acceptance criteria**: stack deploys to a single-node k3s from the chart; documented restore drill succeeds; load target (to be set in M7 review) met.

## Standing backlog (unscheduled)

Reachability analysis, root cause analysis clustering, DefectDojo/Dependency Track import, SonarQube/Snyk/CodeQL native connectors beyond SARIF, Jenkins/Azure DevOps ingestion, business unit scorecards, compliance mapping.
