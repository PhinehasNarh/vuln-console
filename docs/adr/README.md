# Architecture Decision Records

Significant decisions are recorded here and never rewritten; superseding a decision means a new ADR that references the old one.

| ADR | Title | Status |
|-----|-------|--------|
| [0001](0001-python-fastapi-backend.md) | Python + FastAPI backend | Accepted |
| [0002](0002-modular-monolith.md) | Modular monolith with DDD bounded contexts | Accepted |
| [0003](0003-monorepo.md) | Monorepo | Accepted |
| [0004](0004-nats-jetstream.md) | NATS JetStream as event bus | Accepted |
| [0005](0005-postgresql-system-of-record.md) | PostgreSQL as system of record | Accepted |
| [0006](0006-storage-responsibilities.md) | Storage split: OpenSearch, Redis, MinIO | Accepted |
| [0007](0007-canonical-finding-fingerprint.md) | Canonical finding model and fingerprinting | Accepted |
| [0008](0008-plugin-connectors.md) | Plugin-based ingestion connectors | Accepted |
| [0009](0009-authentication-rbac.md) | JWT authentication and RBAC | Accepted |
| [0010](0010-ai-provider-abstraction.md) | AI provider abstraction | Accepted |
| [0011](0011-frontend-rest-first.md) | React frontend, REST-first API | Accepted |
| [0012](0012-edge-observability.md) | Traefik edge and observability stack | Accepted |
| [0013](0013-worker-nats-py.md) | Worker consumes NATS with nats-py directly | Accepted |

Template: Status, Date, Context, Decision, Consequences.
