# ADR-0011: React frontend, REST-first API

- Status: Accepted
- Date: 2026-07-02

## Context

The platform needs role-specific dashboards and triage UIs, plus both REST and GraphQL APIs per requirements. Building both API styles before the domain stabilizes doubles surface area for no early value.

## Decision

- **Frontend**: React 18 + TypeScript + Vite SPA, TanStack Query for server state, TanStack Table for finding grids. Scaffolded in Milestone 1.
- **API**: versioned REST (`/api/v1`) first, generated OpenAPI as the contract, conventions in docs/api/conventions.md. GraphQL (Strawberry) is added in Milestone 7 as a second interface over the same application services, once entities and relationships have stabilized.

## Consequences

- Positive: one contract to stabilize early; the SPA and CLI consume the same REST API, proving it.
- Negative: GraphQL consumers wait until Milestone 7.
- Mitigation: application services are transport-agnostic by design, so GraphQL is additive, not a refactor.
