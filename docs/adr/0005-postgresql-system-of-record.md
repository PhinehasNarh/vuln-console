# ADR-0005: PostgreSQL as system of record

- Status: Accepted
- Date: 2026-07-02

## Context

The domain model is relational (findings link vulnerabilities, packages, assets, workflow records) and demands transactional integrity for triage state transitions and audit logging. Raw scanner payloads are heterogeneous and schema-less.

## Decision

PostgreSQL 16 is the single system of record. Each bounded context owns a dedicated schema namespace (e.g. `triage.*`). Raw scanner payloads, evidence blobs, and event snapshots are stored in JSONB columns; everything the platform reasons about is normalized into typed columns.

## Consequences

- Positive: constraints and transactions where correctness matters; JSONB keeps scanner data lossless; one database to back up.
- Negative: JSONB queries are not the search surface; that job belongs to OpenSearch (ADR-0006).
- Mitigation: OpenSearch projections are rebuildable from PostgreSQL plus the event streams; PostgreSQL never depends on OpenSearch.
