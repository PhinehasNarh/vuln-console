# ADR-0003: Monorepo

- Status: Accepted
- Date: 2026-07-02

## Context

Backend, frontend, deployment configuration, operations configuration, and documentation must evolve together. Polyrepo would add cross-repo versioning and CI orchestration for a single-operator project.

## Decision

One repository containing `backend/`, `frontend/`, `deploy/`, `ops/`, and `docs/`.

## Consequences

- Positive: atomic changes across API contract, client, and docs; one CI pipeline; one place to search.
- Negative: repository grows large over time; CI must scope jobs by path to stay fast.
- Mitigation: CI path filters from Milestone 1; if a context is extracted to its own service (ADR-0002), it may graduate to its own repository at that time.
