"""Auth and user endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from vulnconsole.contexts.identity.api.deps import (
    Principal,
    get_current_principal,
    require_permission,
)
from vulnconsole.contexts.identity.application import service
from vulnconsole.contexts.identity.application.schemas import (
    ApiTokenCreatedOut,
    CreateApiTokenRequest,
    CreateUserRequest,
    RefreshRequest,
    TokenPair,
    UserOut,
)
from vulnconsole.contexts.identity.domain.roles import TOKENS_MANAGE, USERS_MANAGE
from vulnconsole.shared.config import get_settings
from vulnconsole.shared.db import get_db_session
from vulnconsole.shared.deps import get_redis
from vulnconsole.shared.problems import ProblemError
from vulnconsole.shared.ratelimit import within_rate_limit
from vulnconsole.shared.security import InvalidTokenError, create_token, decode_token

router = APIRouter(tags=["identity"])


def _token_pair(user_id: uuid.UUID, role: str) -> TokenPair:
    return TokenPair(
        access_token=create_token(subject=str(user_id), role=role, kind="access"),
        refresh_token=create_token(subject=str(user_id), role=role, kind="refresh"),
    )


@router.post("/auth/token", response_model=TokenPair)
async def login(
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> TokenPair:
    client_ip = request.client.host if request.client else "unknown"
    allowed = await within_rate_limit(
        redis,
        f"ratelimit:login:{client_ip}",
        limit=get_settings().login_rate_limit_per_minute,
        window_seconds=60,
    )
    if not allowed:
        raise ProblemError(
            status=429,
            title="Too many login attempts",
            detail="Retry in a minute",
            slug="rate-limited",
            headers={"Retry-After": "60"},
        )

    user = await service.authenticate(session, form.username, form.password)
    if user is None:
        service.record_audit(
            session,
            actor=f"ip:{client_ip}",
            action="auth.login_failed",
            entity_type="user",
            entity_id=form.username,
        )
        await session.commit()
        raise ProblemError(
            status=401,
            title="Unauthenticated",
            detail="Invalid username or password",
            slug="unauthenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    service.record_audit(
        session,
        actor=f"user:{user.id}",
        action="auth.login",
        entity_type="user",
        entity_id=str(user.id),
    )
    await session.commit()
    return _token_pair(user.id, user.role)


@router.post("/auth/refresh", response_model=TokenPair)
async def refresh(
    body: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenPair:
    try:
        claims = decode_token(body.refresh_token, expected_kind="refresh")
    except InvalidTokenError as exc:
        raise ProblemError(
            status=401,
            title="Unauthenticated",
            detail="Invalid or expired refresh token",
            slug="unauthenticated",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    user = await service.get_user_by_id(session, uuid.UUID(claims.sub))
    if user is None or not user.is_active:
        raise ProblemError(
            status=401,
            title="Unauthenticated",
            detail="User no longer exists or is inactive",
            slug="unauthenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _token_pair(user.id, user.role)


@router.get("/users/me", response_model=UserOut)
async def me(
    principal: Annotated[Principal, Depends(get_current_principal)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserOut:
    if principal.kind != "user":
        raise ProblemError(
            status=403,
            title="Forbidden",
            detail="API tokens have no user profile",
            slug="forbidden",
        )
    user = await service.get_user_by_id(session, principal.id)
    if user is None:  # pragma: no cover - principal resolution already checked
        raise ProblemError(status=404, title="Not found", detail="User not found", slug="not-found")
    return UserOut.model_validate(user)


@router.post("/users", response_model=UserOut, status_code=201)
async def create_user(
    body: CreateUserRequest,
    principal: Annotated[Principal, Depends(require_permission(USERS_MANAGE))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserOut:
    user = await service.create_user(
        session,
        actor=principal.actor,
        username=body.username,
        password=body.password,
        role=body.role,
    )
    return UserOut.model_validate(user)


@router.post("/auth/api-tokens", response_model=ApiTokenCreatedOut, status_code=201)
async def create_api_token(
    body: CreateApiTokenRequest,
    principal: Annotated[Principal, Depends(require_permission(TOKENS_MANAGE))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ApiTokenCreatedOut:
    api_token, plaintext = await service.create_api_token(
        session, actor=principal.actor, name=body.name, created_by=principal.id
    )
    return ApiTokenCreatedOut(id=api_token.id, name=api_token.name, token=plaintext)
