# ADR-0004: NATS JetStream as event bus

- Status: Accepted
- Date: 2026-07-02

## Context

The finding pipeline (ingest, normalize, enrich, score, notify) is asynchronous and stage-based. Stages must be idempotent and replayable (projection rebuilds, backfills after connector fixes). Candidates: NATS JetStream and RabbitMQ.

## Decision

NATS with JetStream enabled, file-backed storage, streams as defined in docs/architecture/service-decomposition.md.

## Rationale

- Single small binary, trivial to operate in a homelab.
- Durable streams with replay and consumer acknowledgement floors; RabbitMQ queues are consume-once by default and streams support arrived later and less idiomatically.
- Subject hierarchy (`normalization.finding.created`) maps one-to-one to the domain event catalog; wildcard consumers (`triage.>`) fit the projection builder.

## Consequences

- Positive: replayable pipeline, negligible operational cost, clean event naming.
- Negative: no complex routing topologies (not needed); smaller ecosystem of tooling than RabbitMQ.
- Mitigation: the event publisher lives behind a `shared` interface; swapping transports would touch one module.
