# API Conventions

These conventions bind every endpoint from Milestone 1 onward. The generated OpenAPI document at `/api/v1/openapi.json` is the contract; this page defines the rules the contract follows.

## Versioning

- Base path: `/api/v1`. Breaking changes require `/api/v2`; additive changes (new fields, new endpoints) do not bump the version.
- Deprecations are announced via the `Deprecation` and `Sunset` response headers at least one milestone before removal.

## Authentication

- `Authorization: Bearer <token>` on every request except `/healthz`, `/readyz`, and the token endpoints.
- Two token kinds, one header: short-lived user JWTs (interactive clients) and long-lived hashed API tokens (CI ingestion, ingestion-scoped by default). See ADR-0009.
- 401 for missing/invalid credentials, 403 for valid credentials without permission. Authorization denials are audit-logged.

## Resources and naming

- Plural kebab-case collection paths: `/api/v1/findings`, `/api/v1/risk-acceptances`.
- Identifiers are UUIDv7 in path segments: `/api/v1/findings/{finding_id}`.
- Sub-resources for owned relations: `/api/v1/findings/{finding_id}/evidence`.
- Actions that are not CRUD use verb sub-paths: `POST /api/v1/findings/{finding_id}/transitions`.

## Pagination

Cursor-based on every collection endpoint:

```
GET /api/v1/findings?limit=50&cursor=eyJpZCI6...
```

```json
{
  "data": [ ],
  "pagination": {
    "next_cursor": "eyJpZCI6...",
    "has_more": true,
    "limit": 50
  }
}
```

- `limit` defaults to 50, max 200.
- Cursors are opaque; clients must not construct them.

## Filtering

Query parameters, combinable, ANDed:

- Equality: `?severity=critical&scanner=trivy`
- Multi-value (ORed within the field): `?severity=critical,high`
- Ranges with `_gte` / `_lte` suffixes: `?epss_gte=0.5&first_seen_lte=2026-01-01`
- Booleans: `?kev=true&internet_facing=true`
- Free text: `?q=deserialization` (OpenSearch-backed)

Searchable fields on findings include: CVE, CWE, repository, package, language, severity, EPSS, KEV, scanner, commit, branch, owner, tag, SLA state, business unit.

## Sorting

`?sort=-risk_score,first_seen`: comma-separated fields, `-` prefix for descending. Default sort is documented per endpoint.

## Errors

RFC 9457 problem details, `Content-Type: application/problem+json`:

```json
{
  "type": "https://vulnconsole.dev/problems/validation-error",
  "title": "Validation failed",
  "status": 422,
  "detail": "2 fields failed validation",
  "instance": "/api/v1/scans",
  "errors": [
    { "field": "scanner_id", "message": "unknown scanner" }
  ],
  "trace_id": "otel trace id for correlation"
}
```

Status usage: 400 malformed, 401 unauthenticated, 403 unauthorized, 404 not found (also for resources hidden by scoping), 409 conflict, 422 validation, 429 rate limited, 5xx server.

## Rate limiting

Redis-backed per token, in addition to edge limits at Traefik. Responses carry `RateLimit-Limit`, `RateLimit-Remaining`, `RateLimit-Reset`; 429 includes `Retry-After`.

## Ingestion specifics

- `POST /api/v1/scans` accepts multipart upload or a JSON body referencing a webhook payload; max artifact size enforced (default 50 MB), content sniffed by connector `sniff()` rather than trusting extensions or Content-Type.
- `Idempotency-Key` header supported: replays return the original response instead of creating duplicate scans.

## Timestamps and encoding

- All timestamps are RFC 3339 UTC (`2026-07-02T12:00:00Z`).
- Request and response bodies are UTF-8 JSON; field names are snake_case.
