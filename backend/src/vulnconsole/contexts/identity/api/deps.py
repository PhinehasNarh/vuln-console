"""Authenticated principal resolution and permission enforcement."""

import uuid
from collections.abc import Awaitable, Callable
from typing import Annotated, Literal

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from vulnconsole.contexts.identity.application import service
from vulnconsole.contexts.identity.domain.roles import API_TOKEN_PERMISSIONS, ROLE_PERMISSIONS
from vulnconsole.shared.db import get_db_session
from vulnconsole.shared.problems import ProblemError
from vulnconsole.shared.security import InvalidTokenError, decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


class Principal(BaseModel):
    kind: Literal["user", "token"]
    id: uuid.UUID
    name: str
    role: str | None
    permissions: frozenset[str]

    @property
    def actor(self) -> str:
        return f"{self.kind}:{self.id}"


def _unauthorized(detail: str) -> ProblemError:
    return ProblemError(
        status=401,
        title="Unauthenticated",
        detail=detail,
        slug="unauthenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_principal(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Principal:
    if not token:
        raise _unauthorized("Missing bearer token")

    if token.startswith(service.API_TOKEN_PREFIX):
        api_token = await service.resolve_api_token(session, token)
        if api_token is None:
            raise _unauthorized("Unknown or revoked API token")
        return Principal(
            kind="token",
            id=api_token.id,
            name=api_token.name,
            role=None,
            permissions=API_TOKEN_PERMISSIONS,
        )

    try:
        claims = decode_token(token, expected_kind="access")
    except InvalidTokenError as exc:
        raise _unauthorized("Invalid or expired access token") from exc
    user = await service.get_user_by_id(session, uuid.UUID(claims.sub))
    if user is None or not user.is_active:
        raise _unauthorized("User no longer exists or is inactive")
    return Principal(
        kind="user",
        id=user.id,
        name=user.username,
        role=user.role,
        permissions=ROLE_PERMISSIONS.get(user.role, frozenset()),
    )


def require_permission(permission: str) -> Callable[..., Awaitable["Principal"]]:
    async def dependency(
        principal: Annotated[Principal, Depends(get_current_principal)],
        request: Request,
        session: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> Principal:
        if permission not in principal.permissions:
            service.record_audit(
                session,
                actor=principal.actor,
                action="authz.denied",
                entity_type="endpoint",
                entity_id=request.url.path,
                detail={"permission": permission},
            )
            await session.commit()
            raise ProblemError(
                status=403,
                title="Forbidden",
                detail=f"Requires permission {permission!r}",
                slug="forbidden",
            )
        return principal

    return dependency
