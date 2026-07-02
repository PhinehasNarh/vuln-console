# ADR-0002: Modular monolith with DDD bounded contexts

- Status: Accepted
- Date: 2026-07-02

## Context

The meta-requirements ask for independently deployable, event-driven components, but the first deployment target is a single-operator homelab on Docker Compose. Running 11 microservices from day one multiplies build, deploy, and debugging cost before any feature value exists.

## Decision

One Python codebase structured as 11 bounded contexts (see docs/architecture/service-decomposition.md), deployed as two processes: an API service and a worker service, sharing the same image with different entrypoints.

Enforced boundaries:

- Each context owns its tables in a dedicated PostgreSQL schema namespace.
- Contexts never import another context's `domain` or `infrastructure` layers (lint-enforced from Milestone 1 via import-linter).
- Cross-context communication is NATS events or a context's `application` interface, nothing else.

## Consequences

- Positive: homelab-operable; refactoring across contexts is atomic; extraction to microservices later is a packaging exercise (streams and schemas are already separated).
- Negative: discipline is required to keep boundaries honest; a monolith makes boundary violations easy.
- Mitigation: import-linter contract in CI; event-first design reviewed at each milestone.
