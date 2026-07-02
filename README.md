# Codebase Vulnerability Triage & Remediation Console

A self-hosted, single pane of glass for application security findings. The platform ingests results from many security scanners, normalizes them into a canonical model, deduplicates and correlates findings, enriches them with CVE/CWE/EPSS/KEV intelligence, scores risk, drives triage and exception workflows, recommends remediations, and serves role-specific dashboards.

Built homelab-first (Docker Compose), designed to evolve into an enterprise platform (Kubernetes).

## Why

Security teams drown in duplicated, unprioritized scanner output. This console exists to answer:

- What actually matters?
- What should be fixed first?
- Can this finding be automatically remediated?
- Is this vulnerability already fixed elsewhere?
- What is the business risk?
- What evidence supports this recommendation?

## Status

**Milestone 1: walking skeleton, code complete.** Upload a SARIF report, watch it become deduplicated findings in a keyboard-first UI, behind JWT auth, RBAC, and an audit trail. Unit tests, typecheck, and image builds pass; the live end-to-end run is scripted for the next session in [docs/next-session.md](docs/next-session.md). Roadmap: [docs/roadmap.md](docs/roadmap.md).

## Architecture at a glance

- **Backend**: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0, structured as a modular monolith with 11 DDD bounded contexts communicating over NATS JetStream events
- **Frontend**: React 18 + TypeScript + Vite (scaffolded in Milestone 1)
- **Data**: PostgreSQL (system of record), OpenSearch (search and analytics), Redis (cache, rate limiting), MinIO (raw scan artifacts and SBOMs)
- **Edge and observability**: Traefik, Prometheus, Grafana, OpenTelemetry, structlog

Full details: [docs/architecture/overview.md](docs/architecture/overview.md)

## Documentation map

| Document | Purpose |
|----------|---------|
| [docs/architecture/overview.md](docs/architecture/overview.md) | System context and container diagrams, data flow, principles |
| [docs/architecture/tech-stack.md](docs/architecture/tech-stack.md) | Technology decisions with rationale |
| [docs/architecture/domain-model.md](docs/architecture/domain-model.md) | Entity catalog, ER diagram, finding lifecycle |
| [docs/architecture/service-decomposition.md](docs/architecture/service-decomposition.md) | Bounded contexts, event catalog, dependency graph |
| [docs/adr/](docs/adr/) | Architecture Decision Records (ADR-0001 to ADR-0012) |
| [docs/architecture/diagrams.md](docs/architecture/diagrams.md) | Diagram index, deployment topology, auth flow |
| [docs/api/conventions.md](docs/api/conventions.md) | API versioning, pagination, filtering, errors, auth |
| [docs/security/threat-model.md](docs/security/threat-model.md) | STRIDE threat model of the platform itself |
| [docs/roadmap.md](docs/roadmap.md) | Milestones M0 to M8 with acceptance criteria |
| [docs/design/design-language.md](docs/design/design-language.md) | The Ledger design language: tokens, color, type, motion |
| [docs/design/ux-blueprint.md](docs/design/ux-blueprint.md) | Personas, journeys, interaction architecture |
| [docs/developer-guide.md](docs/developer-guide.md) | Dev environment, conventions, adding a connector |
| [docs/operator-guide.md](docs/operator-guide.md) | Running, backups, upgrades, accounts |
| [docs/overview-for-everyone.md](docs/overview-for-everyone.md) | Non-technical explanation and glossary |
| [docs/next-session.md](docs/next-session.md) | Verification runbook for the next working session |

## Quickstart

Requires Docker Desktop (or any Docker Engine with the compose plugin).

```bash
cd deploy/compose
cp .env.example .env        # change every credential; set VULNCONSOLE_SEED_ADMIN_PASSWORD
docker compose up -d
docker compose ps           # all services should report healthy
```

Then open http://localhost and sign in as `admin` with the seed password from your `.env`. Upload `deploy/sample-data/semgrep-example.sarif` to see the pipeline run end to end. Full walkthrough: [docs/next-session.md](docs/next-session.md).

Local endpoints after startup:

| Service | Endpoint |
|---------|----------|
| Web UI (via Traefik) | http://localhost |
| API + OpenAPI docs | http://localhost/api/v1/docs |
| Grafana | http://localhost:3000 |
| Prometheus | http://localhost:9090 |
| MinIO console | http://localhost:9001 |
| OpenSearch | http://localhost:9200 |
| NATS monitoring | http://localhost:8222 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

Tear down with `docker compose down` (add `-v` to drop volumes).

Note: images build and the compose config validates, but the stack has not yet been brought up live end to end on this machine; the scripted verification pass is [docs/next-session.md](docs/next-session.md). Remove this note once it passes.

## Repository layout

```
backend/    Python modular monolith (bounded contexts under src/vulnconsole/contexts)
frontend/   React SPA (scaffolded in Milestone 1)
deploy/     Docker Compose now, Kubernetes later
ops/        Prometheus, Grafana, Traefik configuration
docs/       Architecture, ADRs, API, security, roadmap
```

## Contributing conventions

- Writing style: no em dashes or en dashes in any file (docs, comments, commit messages). CI enforces this.
- Every feature ships with architecture notes, tests, and documentation.
- ADRs record every significant decision; propose changes via a new ADR, not by editing accepted ones.
