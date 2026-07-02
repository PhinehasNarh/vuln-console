"""Opaque cursor pagination primitives (docs/api/conventions.md)."""

import base64
import binascii
import json
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from vulnconsole.shared.problems import ProblemError

DEFAULT_LIMIT = 50
MAX_LIMIT = 200

T = TypeVar("T")


class PageMeta(BaseModel):
    next_cursor: str | None
    has_more: bool
    limit: int


class Page(BaseModel, Generic[T]):
    data: list[T]
    pagination: PageMeta


def encode_cursor(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode()


def decode_cursor(cursor: str) -> dict[str, Any]:
    try:
        decoded = json.loads(base64.urlsafe_b64decode(cursor.encode()))
    except (binascii.Error, ValueError) as exc:
        raise ProblemError(
            status=400, title="Invalid cursor", detail="The cursor is malformed", slug="bad-cursor"
        ) from exc
    if not isinstance(decoded, dict):
        raise ProblemError(
            status=400, title="Invalid cursor", detail="The cursor is malformed", slug="bad-cursor"
        )
    return decoded


def clamp_limit(limit: int) -> int:
    return max(1, min(limit, MAX_LIMIT))
