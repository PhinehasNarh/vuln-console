"""Scan endpoints: upload and inspection."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Form, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vulnconsole.contexts.identity.api.deps import Principal, require_permission
from vulnconsole.contexts.identity.domain.roles import SCANS_INGEST, SCANS_READ
from vulnconsole.contexts.ingestion.application import service
from vulnconsole.contexts.ingestion.application.schemas import ScanOut
from vulnconsole.contexts.ingestion.domain.models import Scan
from vulnconsole.shared.db import get_db_session
from vulnconsole.shared.deps import get_event_bus
from vulnconsole.shared.events import EventBus
from vulnconsole.shared.pagination import (
    DEFAULT_LIMIT,
    Page,
    PageMeta,
    clamp_limit,
    decode_cursor,
    encode_cursor,
)
from vulnconsole.shared.problems import ProblemError

router = APIRouter(tags=["ingestion"])


@router.post("/scans", response_model=ScanOut, status_code=202)
async def upload_scan(
    file: UploadFile,
    repository: Annotated[str, Form(min_length=1, max_length=300)],
    principal: Annotated[Principal, Depends(require_permission(SCANS_INGEST))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    bus: Annotated[EventBus, Depends(get_event_bus)],
    branch: Annotated[str | None, Form(max_length=200)] = None,
    commit_sha: Annotated[str | None, Form(max_length=64)] = None,
    format: Annotated[str | None, Form(max_length=50)] = None,
) -> ScanOut:
    content = await file.read()
    scan = await service.create_scan(
        session,
        bus,
        actor=principal.actor,
        repository=repository,
        branch=branch,
        commit_sha=commit_sha,
        filename=file.filename,
        content=content,
        format_id=format,
    )
    return ScanOut.model_validate(scan)


@router.get("/scans", response_model=Page[ScanOut])
async def list_scans(
    principal: Annotated[Principal, Depends(require_permission(SCANS_READ))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    repository: str | None = None,
    status: str | None = None,
    limit: int = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> Page[ScanOut]:
    limit = clamp_limit(limit)
    query = select(Scan).order_by(Scan.created_at.desc(), Scan.id.desc())
    if repository:
        query = query.where(Scan.repository == repository)
    if status:
        query = query.where(Scan.status == status)
    if cursor:
        position = decode_cursor(cursor)
        created_at = datetime.fromisoformat(str(position["c"]))
        last_id = uuid.UUID(str(position["i"]))
        query = query.where(
            (Scan.created_at < created_at)
            | ((Scan.created_at == created_at) & (Scan.id < last_id))
        )
    rows = list(await session.scalars(query.limit(limit + 1)))
    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = (
        encode_cursor({"c": rows[-1].created_at.isoformat(), "i": str(rows[-1].id)})
        if has_more and rows
        else None
    )
    return Page(
        data=[ScanOut.model_validate(row) for row in rows],
        pagination=PageMeta(next_cursor=next_cursor, has_more=has_more, limit=limit),
    )


@router.get("/scans/{scan_id}", response_model=ScanOut)
async def get_scan(
    scan_id: uuid.UUID,
    principal: Annotated[Principal, Depends(require_permission(SCANS_READ))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ScanOut:
    scan = await service.get_scan(session, scan_id)
    if scan is None:
        raise ProblemError(status=404, title="Not found", detail="Scan not found", slug="not-found")
    return ScanOut.model_validate(scan)
