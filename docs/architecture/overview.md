# Architecture Overview

## Vision

A centralized platform that turns raw, noisy scanner output into prioritized, evidence-backed, actionable security work. The console is the single pane of glass for application security findings across a homelab (and later, an enterprise) estate.

## Goals

1. Reduce alert fatigue: one canonical finding per real issue, regardless of how many scanners report it.
2. Prioritize by real risk: exploitability (EPSS, KEV), severity (CVSS), asset criticality, and reachability, not raw severity alone.
3. Make remediation cheap: concrete fix guidance, dependency upgrade paths, and eventually automated fix PRs.
4. Keep humans accountable: triage workflows, exceptions with expiry, ownership, SLAs, and a complete audit trail.

## Architectural principles

- **Modular monolith first** (ADR-0002): one codebase, strict bounded contexts, two deployable processes (API + worker). Contexts communicate through NATS events and application-service interfaces only, never through each other's domain internals. This makes later extraction into microservices a packaging exercise, not a rewrite.
- **Event-driven pipeline**: ingestion, normalization, enrichment, scoring, and notification are asynchronous stages connected by durable JetStream streams. Each stage is idempotent and replayable.
- **API-first**: every capability is exposed through the versioned REST API before any UI is built on it. The frontend is just another API client.
- **Plugin extensibility**: scanner connectors are plugins behind a stable protocol (ADR-0008). Adding a scanner never modifies core code.
- **Secure by design**: the platform stores vulnerability data and real secrets found by scanners. It is itself a high-value target and is threat modeled accordingly (docs/security/threat-model.md).

## System context (C4 level 1)

```mermaid
flowchart TB
    seceng["Security Engineer"]
    dev["Developer"]
    mgr["Manager"]

    subgraph console["Vulnerability Triage & Remediation Console"]
        core["Ingest, normalize, correlate, enrich,\nscore, triage, remediate, report"]
    end

    scanners["Scanners and CI pipelines\nSemgrep, CodeQL, Trivy, Grype, Gitleaks,\nTruffleHog, Syft, SonarQube, Snyk, ..."]
    feeds["Vulnerability intelligence\nNVD, OSV, EPSS, CISA KEV"]
    scm["Source control\nGitHub, GitLab"]
    trackers["Ticketing\nJira, GitHub Issues, GitLab Issues"]
    chat["Messaging\nSlack, Teams, email"]
    llm["LLM providers\nAnthropic API, Ollama (local)"]

    seceng -->|triage, exceptions, dashboards| console
    dev -->|fix guidance, repo findings| console
    mgr -->|KPIs, risk posture| console

    scanners -->|SARIF, CycloneDX, SPDX, native JSON, webhooks| console
    feeds -->|scheduled sync| console
    console -->|fix PRs, issue links| scm
    console -->|create and update tickets| trackers
    console -->|notifications| chat
    console -->|summaries, guidance, NL Q&A| llm
```

## Container view (C4 level 2)

```mermaid
flowchart TB
    user["Browser / CLI / CI"]

    subgraph edge["Edge"]
        traefik["Traefik\nTLS, secure headers, routing"]
    end

    subgraph apps["Application (modular monolith)"]
        spa["Frontend SPA\nReact + TypeScript"]
        api["API service\nFastAPI: REST now, GraphQL later"]
        worker["Worker service\nNATS consumers: parse, normalize,\nenrich, score, notify"]
    end

    subgraph data["Data plane"]
        pg[("PostgreSQL\nsystem of record")]
        os[("OpenSearch\nsearch + analytics projections")]
        redis[("Redis\ncache, rate limits")]
        minio[("MinIO\nraw artifacts, SBOMs")]
        nats[("NATS JetStream\ndurable event streams")]
    end

    subgraph obs["Observability"]
        prom["Prometheus"]
        graf["Grafana"]
    end

    user --> traefik
    traefik --> spa
    traefik --> api
    api --> pg
    api --> redis
    api --> os
    api --> minio
    api -->|publish| nats
    nats -->|consume| worker
    worker --> pg
    worker --> os
    worker --> minio
    worker -->|publish| nats
    prom -->|scrape| api
    prom -->|scrape| worker
    prom -->|scrape| traefik
    graf --> prom
```

The API and worker are the same codebase with different composition roots (`platform/api`, `platform/worker`). Both load the bounded contexts under `backend/src/vulnconsole/contexts/`; the API mounts their routers, the worker subscribes their event handlers.

## The finding pipeline

The core data flow, from scanner output to actionable finding:

```mermaid
sequenceDiagram
    participant CI as CI / Upload / Webhook
    participant API as API (Ingestion)
    participant M as MinIO
    participant N as NATS JetStream
    participant W as Worker
    participant PG as PostgreSQL
    participant OS as OpenSearch

    CI->>API: POST /api/v1/scans (SARIF, CycloneDX, native JSON)
    API->>M: store raw artifact
    API->>PG: create Scan (status: received)
    API->>N: publish ingestion.scan.received
    N->>W: deliver
    W->>M: fetch artifact
    W->>W: connector plugin parses to raw findings
    W->>N: publish ingestion.scan.parsed
    W->>W: normalize, fingerprint, dedupe
    W->>PG: upsert canonical Findings
    W->>N: publish normalization.finding.created / updated
    W->>W: enrich (CVE, CWE, EPSS, KEV)
    W->>W: score risk (CVSS x EPSS x KEV x criticality)
    W->>PG: persist enrichment + score
    W->>OS: index finding projection
    W->>N: publish risk.finding.scored
    Note over N,W: Notifications and ticket automation<br/>consume downstream events
```

Every stage is idempotent: replaying `ingestion.scan.received` re-parses without duplicating findings, because canonical identity is the deterministic fingerprint (ADR-0007).

## Deployment view

- **Now (M0+)**: single Docker Compose stack. Infrastructure services in `deploy/compose/docker-compose.yml`; API, worker, and frontend containers join the stack in Milestone 1.
- **Later (M8)**: Kubernetes manifests/Helm chart. The monolith's contexts can be split into separately scaled deployments (worker per pipeline stage) without code changes because all cross-context communication already flows through NATS.

## Related documents

- Technology choices and rationale: [tech-stack.md](tech-stack.md)
- Bounded contexts and events: [service-decomposition.md](service-decomposition.md)
- Entities and lifecycle: [domain-model.md](domain-model.md)
- Decision records: [../adr/](../adr/)
