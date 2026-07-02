# Architecture Diagrams

Index of every diagram in the documentation set, plus the deployment and runtime diagrams that did not fit elsewhere. All diagrams are Mermaid and render on GitHub.

| Diagram | Where |
|---------|-------|
| C4 level 1: system context | [overview.md](overview.md) |
| C4 level 2: containers | [overview.md](overview.md) |
| Finding pipeline (sequence) | [overview.md](overview.md) |
| ER diagram (domain model) | [domain-model.md](domain-model.md) |
| Finding lifecycle (state) | [domain-model.md](domain-model.md) |
| Bounded-context dependency graph | [service-decomposition.md](service-decomposition.md) |
| Trust boundaries | [../security/threat-model.md](../security/threat-model.md) |
| Deployment topology (Compose) | below |
| Authentication flow | below |
| Scan status lifecycle | below |

## Deployment topology (Docker Compose, Milestone 1)

Only Traefik publishes ports to the network; every admin and data port binds to loopback. The `edge` network carries routed traffic, the `internal` network everything else.

Color key: blue = application containers, teal = stateful data stores, gray = edge and observability. "loopback" means the port is reachable only from the host machine itself.

```mermaid
flowchart LR
    browser(["Browser / CLI / CI runner"])

    subgraph host["Docker host, compose project: vulnconsole"]
        subgraph edge["network: edge (routed traffic)"]
            traefik["traefik<br/>ports 80 + 443 (published)"]
            frontend["frontend<br/>nginx serving the SPA"]
            api["api<br/>FastAPI on 8000"]
        end
        subgraph internal["network: internal (nothing published)"]
            worker["worker<br/>NATS consumers"]
            pg[("postgres<br/>5432 loopback")]
            redis[("redis<br/>6379 loopback")]
            minio[("minio<br/>9000 + 9001 loopback")]
            osearch[("opensearch<br/>9200 loopback")]
            nats[("nats<br/>4222 + 8222 loopback")]
            prom["prometheus<br/>9090 loopback"]
            graf["grafana<br/>3000 loopback"]
        end
    end

    browser -->|"HTTP(S)"| traefik
    traefik -->|"route: /"| frontend
    traefik -->|"route: /api"| api
    api -->|"SQL"| pg
    api -->|"cache, rate limits"| redis
    api -->|"store artifacts"| minio
    api -->|"publish events"| nats
    worker -->|"SQL"| pg
    worker -->|"fetch artifacts"| minio
    worker -->|"consume events"| nats
    prom -.->|"scrape"| traefik
    graf -->|"query"| prom

    classDef platform fill:#2b6cb0,stroke:#234f80,color:#ffffff
    classDef store fill:#2c7a7b,stroke:#215a5b,color:#ffffff
    classDef infra fill:#616a75,stroke:#49505a,color:#ffffff
    classDef person fill:#5b4bb7,stroke:#43389a,color:#ffffff
    class frontend,api,worker platform
    class pg,redis,minio,osearch,nats store
    class traefik,prom,graf infra
    class browser person
```

Startup ordering: `api` waits for postgres/redis/nats/minio health, runs `alembic upgrade head`, optionally seeds the admin user, then serves; its own healthcheck is `/readyz`. `worker` starts only after `api` reports healthy, so the schema always exists before consumers run.

## Authentication and authorization flow

```mermaid
sequenceDiagram
    autonumber
    participant B as Browser / CLI
    participant T as Traefik
    participant A as API
    participant R as Redis
    participant PG as PostgreSQL

    B->>T: POST /api/v1/auth/token (username, password)
    T->>A: forward
    A->>R: login rate limit (per client IP, 10/min)
    A->>PG: load user, verify argon2 hash
    A->>PG: append AuditEvent: auth.login
    A-->>B: access JWT (15 min) + refresh JWT (7 d)

    B->>T: GET /api/v1/findings (Authorization: Bearer)
    T->>A: forward
    A->>A: validate JWT, map role to permissions
    Note over A: missing permission: 403 problem+json<br/>and an authz.denied audit event
    A->>PG: query findings (keyset pagination)
    A-->>B: page + next_cursor
```

CI ingestion tokens (`vc_` prefix) travel through the same header, resolve against a hashed token table, and carry only `scans:ingest`; they can never read findings.

## Scan status lifecycle (implemented in M1)

```mermaid
stateDiagram-v2
    [*] --> received : upload accepted, artifact in MinIO
    received --> parsed : worker parsed via connector
    received --> failed : connector error / bad artifact
    parsed --> normalized : canonical findings upserted
    failed --> [*]
    normalized --> [*]
```

Each transition is committed before the next pipeline event publishes, and every stage is idempotent: re-delivery of `ingestion.scan.received` re-parses cleanly, re-delivery of `ingestion.scan.parsed` skips raw findings that already link to a canonical finding.
