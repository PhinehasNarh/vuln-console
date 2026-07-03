"""Time-ordered UUIDv7 identifiers, converted to stdlib UUID for SQLAlchemy."""

import uuid


def uuid7() -> uuid.UUID:
    # Imported lazily so merely referencing this callable as a column default
    # does not load the native extension at module import time.
    import uuid_utils

    return uuid.UUID(bytes=uuid_utils.uuid7().bytes)
