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

**Milestone 0: Architecture and scaffold.** No application code yet. This repository currently contains the full architecture package and infrastructure scaffold. See [docs/roadmap.md](docs/roadmap.md) for what lands next.

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
| [docs/api/conventions.md](docs/api/conventions.md) | API versioning, pagination, filtering, errors, auth |
| [docs/security/threat-model.md](docs/security/threat-model.md) | STRIDE threat model of the platform itself |
| [docs/roadmap.md](docs/roadmap.md) | Milestones M0 to M8 with acceptance criteria |

## Quickstart (infrastructure only)

Requires Docker Desktop (or any Docker Engine with the compose plugin).

```bash
cd deploy/compose
cp .env.example .env        # adjust credentials before first start
docker compose up -d
docker compose ps           # all services should report healthy
```

Local endpoints after startup:

| Service | Endpoint |
|---------|----------|
| Traefik (edge) | http://localhost:80 |
| Grafana | http://localhost:3000 |
| Prometheus | http://localhost:9090 |
| MinIO console | http://localhost:9001 |
| OpenSearch | http://localhost:9200 |
| NATS monitoring | http://localhost:8222 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

Tear down with `docker compose down` (add `-v` to drop volumes).

Note: the compose file is syntax-validated; the stack has not yet been brought up live on this machine (Docker Desktop was not running at scaffold time). Remove this note after the first successful `docker compose up`.

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
