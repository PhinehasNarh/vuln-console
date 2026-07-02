# Technology Stack

Each decision below is recorded as an ADR in [../adr/](../adr/). This page is the summary view.

| Area | Choice | ADR |
|------|--------|-----|
| Backend language and framework | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic | 0001 |
| System structure | Modular monolith, DDD bounded contexts | 0002 |
| Repository strategy | Monorepo | 0003 |
| Event bus | NATS JetStream | 0004 |
| System of record | PostgreSQL 16 (JSONB for raw payloads) | 0005 |
| Search, cache, object storage | OpenSearch, Redis, MinIO | 0006 |
| Finding identity | Canonical model + deterministic fingerprint | 0007 |
| Scanner integration | Plugin connectors via entry points | 0008 |
| AuthN / AuthZ | OAuth2 + JWT, OIDC-ready; RBAC | 0009 |
| AI layer | Provider abstraction; Anthropic first, Ollama local | 0010 |
| Frontend and API style | React + TypeScript + Vite; REST first, GraphQL later | 0011 |
| Edge and observability | Traefik; structlog, OpenTelemetry, Prometheus, Grafana | 0012 |

## Rationale highlights

### Python + FastAPI (ADR-0001)

The ingestion problem is dominated by parsing heterogeneous security formats (SARIF, CycloneDX, SPDX, a dozen native JSON dialects) and talking to intelligence feeds. Python has the strongest ecosystem for both, plus first-class LLM SDKs for the AI layer. FastAPI gives async-native request handling, automatic OpenAPI generation (an API-first requirement), and Pydantic v2 validation at every boundary.

### Modular monolith (ADR-0002)

A homelab does not need 11 microservices; it needs one API container and one worker container that are easy to run, debug, and back up. The discipline that makes later extraction possible is enforced now: contexts own their tables (per-context schema namespaces), expose application services instead of domain objects, and communicate across contexts only via NATS events.

### NATS JetStream over RabbitMQ (ADR-0004)

Single small binary, durable streams with replay (needed for idempotent pipeline stages and backfills), and a subject hierarchy (`normalization.finding.created`) that maps one-to-one onto the domain event catalog. RabbitMQ offers richer routing topologies the platform does not need.

### PostgreSQL + OpenSearch split (ADR-0005, ADR-0006)

PostgreSQL holds the normalized domain model with real constraints and transactions. Raw scanner payloads and evidence blobs live in JSONB columns so no scanner data is ever lost in translation. OpenSearch holds denormalized finding projections for the search surface (CVE, package, repo, EPSS ranges, free text) and dashboard aggregations, where PostgreSQL would need brittle indexes.

### Worker framework note

Decided in Milestone 1 (ADR-0013): the worker uses `nats-py` directly behind the `EventBus` wrapper in `shared/events.py`, with explicit ack/nak retry policy in `platform/worker.py`. FastStream is reevaluated if consumer count or middleware needs grow (M3+).

## Version baseline (M0)

Container images pinned in `deploy/compose/docker-compose.yml`:

| Component | Image |
|-----------|-------|
| PostgreSQL | postgres:16-alpine |
| Redis | redis:7-alpine |
| MinIO | minio/minio (pin to a RELEASE tag at first deploy) |
| OpenSearch | opensearchproject/opensearch:2.17.1 |
| NATS | nats:2.10-alpine |
| Traefik | traefik:v3.1 |
| Prometheus | prom/prometheus:v2.54.1 |
| Grafana | grafana/grafana:11.2.0 |

Python dependencies are declared in `backend/pyproject.toml` with lower-bound constraints; a lock file is generated in Milestone 1 when the first code lands.
