"""API composition root: mounts every context's routers."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from redis.asyncio import Redis
from sqlalchemy import text
from starlette.responses import JSONResponse

import vulnconsole.contexts.ingestion.connectors  # noqa: F401  (registers built-in connectors)
from vulnconsole import __version__
from vulnconsole.contexts.identity.api.router import router as identity_router
from vulnconsole.contexts.ingestion.api.router import router as ingestion_router
from vulnconsole.contexts.ingestion.infrastructure.artifacts import ensure_bucket
from vulnconsole.contexts.normalization.api.router import router as findings_router
from vulnconsole.shared.config import get_settings
from vulnconsole.shared.db import get_engine
from vulnconsole.shared.events import EventBus
from vulnconsole.shared.logging import configure_logging
from vulnconsole.shared.problems import register_problem_handlers

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)

    app.state.redis = Redis.from_url(settings.redis_url)
    app.state.bus = EventBus()
    try:
        await app.state.bus.connect()
    except Exception as exc:
        # Keep serving reads; readyz reports not-ready until NATS returns.
        logger.error("startup.nats_unavailable", error=str(exc))
    try:
        await ensure_bucket()
    except Exception as exc:
        logger.error("startup.minio_unavailable", error=str(exc))

    logger.info("startup.complete", version=__version__)
    yield
    await app.state.bus.close()
    await app.state.redis.aclose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Vulnerability Triage & Remediation Console",
        version=__version__,
        lifespan=lifespan,
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/v1/docs",
        redoc_url=None,
    )
    register_problem_handlers(app)
    app.include_router(identity_router, prefix="/api/v1")
    app.include_router(ingestion_router, prefix="/api/v1")
    app.include_router(findings_router, prefix="/api/v1")

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/readyz", include_in_schema=False)
    async def readyz(request: Request) -> JSONResponse:
        checks: dict[str, bool] = {}
        try:
            async with get_engine().connect() as connection:
                await connection.execute(text("SELECT 1"))
            checks["postgres"] = True
        except Exception:
            checks["postgres"] = False
        checks["nats"] = request.app.state.bus.connected
        try:
            checks["redis"] = bool(await request.app.state.redis.ping())
        except Exception:
            checks["redis"] = False
        ready = all(checks.values())
        return JSONResponse(
            status_code=200 if ready else 503,
            content={"ready": ready, "checks": checks},
        )

    return app


app = create_app()
