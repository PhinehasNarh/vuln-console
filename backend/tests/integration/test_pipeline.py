"""End-to-end pipeline test against live infrastructure (compose stack).

Run with: INTEGRATION=1 pytest tests/integration
Requires postgres, redis, nats, and minio from deploy/compose to be up, and
the schema migrated (alembic upgrade head).
"""

import os
import uuid

import httpx
import pytest
from redis.asyncio import Redis

from tests.conftest import SAMPLE_SARIF
from vulnconsole.contexts.identity.application import service as identity_service
from vulnconsole.contexts.ingestion.application import service as ingestion_service
from vulnconsole.contexts.ingestion.infrastructure.artifacts import ensure_bucket
from vulnconsole.contexts.normalization.application import service as normalization_service
from vulnconsole.shared.config import get_settings
from vulnconsole.shared.db import get_session_factory
from vulnconsole.shared.events import EventBus

pytestmark = pytest.mark.skipif(
    os.environ.get("INTEGRATION") != "1",
    reason="integration tests need the live compose stack (INTEGRATION=1)",
)


@pytest.fixture
async def app_client():
    from vulnconsole.platform.api import create_app

    app = create_app()
    # ASGITransport does not run the lifespan; wire app state manually.
    bus = EventBus()
    await bus.connect()
    await ensure_bucket()
    app.state.bus = bus
    app.state.redis = Redis.from_url(get_settings().redis_url)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, bus
    await app.state.redis.aclose()
    await bus.close()


async def _drive_worker_once(bus: EventBus, scan_id: uuid.UUID) -> None:
    """Run the two pipeline stages inline, exactly what the worker consumers do."""
    factory = get_session_factory()
    async with factory() as session:
        await ingestion_service.parse_scan(session, bus, scan_id)
    async with factory() as session:
        await normalization_service.normalize_scan(session, bus, scan_id)


async def test_upload_twice_yields_no_duplicates(app_client) -> None:
    client, bus = app_client
    run_id = uuid.uuid4().hex[:10]
    repository = f"it/{run_id}"
    username = f"it-admin-{run_id}"
    password = "integration-test-password"

    async with get_session_factory()() as session:
        await identity_service.create_user(
            session, actor="system:test", username=username, password=password, role="admin"
        )

    # Unauthenticated requests are rejected.
    response = await client.get("/api/v1/findings")
    assert response.status_code == 401

    response = await client.post(
        "/api/v1/auth/token", data={"username": username, "password": password}
    )
    assert response.status_code == 200, response.text
    access = response.json()["access_token"]
    auth = {"Authorization": f"Bearer {access}"}

    sarif_bytes = SAMPLE_SARIF.read_bytes()
    scan_ids: list[uuid.UUID] = []
    for _ in range(2):
        response = await client.post(
            "/api/v1/scans",
            headers=auth,
            data={"repository": repository, "branch": "main"},
            files={"file": ("semgrep.sarif", sarif_bytes, "application/json")},
        )
        assert response.status_code == 202, response.text
        scan_id = uuid.UUID(response.json()["id"])
        scan_ids.append(scan_id)
        await _drive_worker_once(bus, scan_id)

    # Both scans fully processed.
    for scan_id in scan_ids:
        response = await client.get(f"/api/v1/scans/{scan_id}", headers=auth)
        assert response.status_code == 200
        assert response.json()["status"] == "normalized"

    # 3 results per upload, 2 uploads, but the same real issues: 2 canonical findings
    # (two SQLi results share rule + file, so v1 fingerprints collapse them).
    response = await client.get(
        "/api/v1/findings", headers=auth, params={"repository": repository}
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 2
    severities = sorted(finding["severity"] for finding in body["data"])
    assert severities == ["critical", "medium"]

    # Detail view links back to all raw findings that fed each canonical one.
    finding_ids = [finding["id"] for finding in body["data"]]
    total_sources = 0
    for finding_id in finding_ids:
        response = await client.get(f"/api/v1/findings/{finding_id}", headers=auth)
        assert response.status_code == 200
        total_sources += len(response.json()["sources"])
    assert total_sources == 6  # 3 raw findings x 2 uploads


async def test_viewer_cannot_ingest(app_client) -> None:
    client, _bus = app_client
    run_id = uuid.uuid4().hex[:10]
    username = f"it-viewer-{run_id}"
    password = "integration-test-password"

    async with get_session_factory()() as session:
        await identity_service.create_user(
            session, actor="system:test", username=username, password=password, role="viewer"
        )

    response = await client.post(
        "/api/v1/auth/token", data={"username": username, "password": password}
    )
    auth = {"Authorization": f"Bearer {response.json()['access_token']}"}

    response = await client.post(
        "/api/v1/scans",
        headers=auth,
        data={"repository": "it/forbidden"},
        files={"file": ("x.sarif", b'{"version":"2.1.0","runs":[]}', "application/json")},
    )
    assert response.status_code == 403
    assert response.headers["content-type"].startswith("application/problem+json")
