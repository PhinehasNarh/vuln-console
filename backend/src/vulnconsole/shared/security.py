"""Password hashing (argon2) and JWT issue/validation."""

from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt
from pwdlib import PasswordHash
from pydantic import BaseModel

from vulnconsole.shared.config import get_settings

_password_hasher = PasswordHash.recommended()

TokenKind = Literal["access", "refresh"]


class InvalidTokenError(Exception):
    pass


class TokenClaims(BaseModel):
    sub: str
    role: str
    kind: TokenKind
    iat: datetime
    exp: datetime


def hash_password(plain: str) -> str:
    return _password_hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _password_hasher.verify(plain, hashed)


def create_token(*, subject: str, role: str, kind: TokenKind) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    ttl = (
        timedelta(minutes=settings.jwt_access_token_minutes)
        if kind == "access"
        else timedelta(days=settings.jwt_refresh_token_days)
    )
    claims = {"sub": subject, "role": role, "kind": kind, "iat": now, "exp": now + ttl}
    return jwt.encode(claims, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str, *, expected_kind: TokenKind) -> TokenClaims:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        claims = TokenClaims.model_validate(payload)
    except (jwt.PyJWTError, ValueError) as exc:
        raise InvalidTokenError("invalid token") from exc
    if claims.kind != expected_kind:
        raise InvalidTokenError(f"expected a {expected_kind} token")
    return claims
