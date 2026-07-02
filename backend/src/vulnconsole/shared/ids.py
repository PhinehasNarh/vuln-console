"""Time-ordered UUIDv7 identifiers, converted to stdlib UUID for SQLAlchemy."""

import uuid

import uuid_utils


def uuid7() -> uuid.UUID:
    return uuid.UUID(bytes=uuid_utils.uuid7().bytes)
