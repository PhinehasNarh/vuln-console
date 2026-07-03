"""Public permission names for other contexts' routers.

Other contexts import permissions from here, never from identity.domain:
domain layers are private to their context (ADR-0002, enforced by import-linter).
"""

from vulnconsole.contexts.identity.domain.roles import (
    FINDINGS_READ,
    FINDINGS_WRITE,
    SCANS_INGEST,
    SCANS_READ,
    TOKENS_MANAGE,
    USERS_MANAGE,
)

__all__ = [
    "FINDINGS_READ",
    "FINDINGS_WRITE",
    "SCANS_INGEST",
    "SCANS_READ",
    "TOKENS_MANAGE",
    "USERS_MANAGE",
]
