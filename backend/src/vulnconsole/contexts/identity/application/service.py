"""Identity application services: authentication, users, API tokens, audit."""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vulnconsole.contexts.identity.domain.models import ApiToken, AuditEvent, User
from vulnconsole.contexts.identity.domain.roles import ROLES
from vulnconsole.shared.problems import ProblemError
from vulnconsole.shared.security import hash_password, verify_password

API_TOKEN_PREFIX = "vc_"  # noqa: S105 (public token-format marker, not a credential)


def record_audit(
    session: AsyncSession,
    *,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: str,
    detail: dict[str, Any] | None = None,
) -> None:
    """Queue an audit event on the session; committed with the mutation it records."""
    session.add(
        AuditEvent(
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            detail=detail or {},
        )
    )


async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
    return await session.scalar(select(User).where(User.username == username))


async def get_user_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await session.get(User, user_id)


async def authenticate(session: AsyncSession, username: str, password: str) -> User | None:
    user = await get_user_by_username(session, username)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


async def create_user(
    session: AsyncSession, *, actor: str, username: str, password: str, role: str
) -> User:
    if role not in ROLES:
        raise ProblemError(
            status=422,
            title="Unknown role",
            detail=f"Role must be one of: {', '.join(ROLES)}",
            slug="unknown-role",
        )
    if await get_user_by_username(session, username) is not None:
        raise ProblemError(
            status=409,
            title="Username taken",
            detail=f"A user named {username!r} already exists",
            slug="conflict",
        )
    user = User(username=username, password_hash=hash_password(password), role=role)
    session.add(user)
    await session.flush()
    record_audit(
        session,
        actor=actor,
        action="user.created",
        entity_type="user",
        entity_id=str(user.id),
        detail={"username": username, "role": role},
    )
    await session.commit()
    return user


def _hash_api_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def create_api_token(
    session: AsyncSession, *, actor: str, name: str, created_by: uuid.UUID
) -> tuple[ApiToken, str]:
    plaintext = API_TOKEN_PREFIX + secrets.token_urlsafe(32)
    api_token = ApiToken(name=name, token_hash=_hash_api_token(plaintext), created_by=created_by)
    session.add(api_token)
    await session.flush()
    record_audit(
        session,
        actor=actor,
        action="api_token.created",
        entity_type="api_token",
        entity_id=str(api_token.id),
        detail={"name": name},
    )
    await session.commit()
    return api_token, plaintext


async def resolve_api_token(session: AsyncSession, plaintext: str) -> ApiToken | None:
    api_token = await session.scalar(
        select(ApiToken).where(
            ApiToken.token_hash == _hash_api_token(plaintext), ApiToken.revoked_at.is_(None)
        )
    )
    if api_token is not None:
        api_token.last_used_at = datetime.now(UTC)
        await session.commit()
    return api_token
