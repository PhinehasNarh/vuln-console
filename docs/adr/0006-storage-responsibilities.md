# ADR-0006: Storage split: OpenSearch, Redis, MinIO

- Status: Accepted
- Date: 2026-07-02

## Context

Beyond the system of record (ADR-0005), the platform needs full-text and faceted search over findings, low-latency caching and rate limiting, and durable storage of uploaded scan artifacts and SBOMs.

## Decision

- **OpenSearch**: denormalized finding projections for the search surface (CVE, CWE, package, repository, severity, EPSS ranges, KEV, scanner, owner, tags) and dashboard aggregations. Projections are derived data, rebuildable at any time.
- **Redis**: cache, API rate limiting, short-lived coordination (e.g. feed sync locks).
- **MinIO**: raw uploaded artifacts (SARIF, scanner JSON, SBOM documents), stored immutably and referenced by Scan records; bucket versioning on.

## Consequences

- Positive: each store does the one job it is best at; losing OpenSearch or Redis loses no data of record.
- Negative: four stateful services in the homelab stack.
- Mitigation: all four are healthchecked in Compose; OpenSearch is single-node with security plugin disabled for the homelab, explicitly flagged as a production gap in the threat model.
