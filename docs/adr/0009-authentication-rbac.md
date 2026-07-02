# ADR-0009: JWT authentication and RBAC

- Status: Accepted
- Date: 2026-07-02

## Context

The platform needs API authentication now, SSO/MFA readiness later, and authorization that scopes what security engineers, developers, and managers can see and change. Findings include real secrets, so access control is not optional even in a homelab.

## Decision

- **AuthN**: OAuth2 password flow issuing short-lived JWT access tokens (15 min) and refresh tokens (7 days), signed with a rotatable server-side key. Long-lived API tokens for CI ingestion, stored hashed, revocable, scoped to ingestion-only by default. The token validation layer accepts OIDC-issued tokens later (Authentik/Keycloak) without endpoint changes, which is the SSO/MFA readiness path.
- **AuthZ**: RBAC. Roles (admin, security-engineer, developer, viewer) map to permissions; team and business-unit membership scopes which resources those permissions apply to. Secret evidence requires an explicit additional permission.

## Consequences

- Positive: standard, auditable, homelab-simple; CI tokens cannot read findings.
- Negative: password auth means the platform stores credentials (argon2 hashed) until SSO arrives.
- Mitigation: MFA and SSO land by fronting with an OIDC provider, not by rebuilding auth; audit log records every authz denial.
