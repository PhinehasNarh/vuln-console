# ADR-0012: Traefik edge and observability stack

- Status: Accepted
- Date: 2026-07-02

## Context

The platform needs TLS termination, secure headers, and routing at the edge, plus structured logs, metrics, traces, and dashboards for its own operation.

## Decision

- **Edge**: Traefik v3. TLS termination, security headers middleware (HSTS, CSP, frame denial), rate limiting middleware at the edge complementing application-level limits in Redis, Docker provider with explicit opt-in labels (`exposedByDefault: false`).
- **Logs**: structlog emitting JSON to stdout; container runtime collects.
- **Metrics**: Prometheus scraping API, worker, and Traefik; Grafana dashboards provisioned from `ops/grafana/`.
- **Traces**: OpenTelemetry SDK with OTLP export, instrumented FastAPI and NATS handlers (a collector/backend such as Tempo or Jaeger joins the stack when tracing lands in Milestone 1+).
- **Health**: every service exposes `/healthz` (liveness) and `/readyz` (readiness, checks Postgres/NATS connectivity).

## Consequences

- Positive: the preferred homelab stack, Kubernetes-portable (same probes, same OTLP).
- Negative: no trace backend in the M0 compose stack; traces are instrumented before they are collected.
- Mitigation: OTLP export is configuration; adding a backend later requires no code change.
