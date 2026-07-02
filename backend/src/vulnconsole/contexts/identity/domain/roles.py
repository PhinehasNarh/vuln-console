"""Roles and their permissions. Team/business-unit scoping arrives in Milestone 4."""

from typing import Final

ADMIN: Final = "admin"
SECURITY_ENGINEER: Final = "security-engineer"
DEVELOPER: Final = "developer"
VIEWER: Final = "viewer"

ROLES: Final = (ADMIN, SECURITY_ENGINEER, DEVELOPER, VIEWER)

FINDINGS_READ: Final = "findings:read"
FINDINGS_WRITE: Final = "findings:write"
SCANS_READ: Final = "scans:read"
SCANS_INGEST: Final = "scans:ingest"
USERS_MANAGE: Final = "users:manage"
TOKENS_MANAGE: Final = "tokens:manage"

ROLE_PERMISSIONS: Final[dict[str, frozenset[str]]] = {
    ADMIN: frozenset(
        {FINDINGS_READ, FINDINGS_WRITE, SCANS_READ, SCANS_INGEST, USERS_MANAGE, TOKENS_MANAGE}
    ),
    SECURITY_ENGINEER: frozenset({FINDINGS_READ, FINDINGS_WRITE, SCANS_READ, SCANS_INGEST}),
    DEVELOPER: frozenset({FINDINGS_READ, SCANS_READ}),
    VIEWER: frozenset({FINDINGS_READ}),
}

# CI tokens can only push scans; they can never read findings (threat model).
API_TOKEN_PERMISSIONS: Final = frozenset({SCANS_INGEST})
