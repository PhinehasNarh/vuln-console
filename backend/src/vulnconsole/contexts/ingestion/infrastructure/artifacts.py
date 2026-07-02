"""MinIO-backed raw artifact storage."""

import io
from functools import lru_cache

import anyio.to_thread
from minio import Minio

from vulnconsole.shared.config import get_settings


@lru_cache
def _client() -> Minio:
    settings = get_settings()
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def _ensure_bucket_sync() -> None:
    bucket = get_settings().minio_bucket_artifacts
    if not _client().bucket_exists(bucket):
        _client().make_bucket(bucket)


async def ensure_bucket() -> None:
    await anyio.to_thread.run_sync(_ensure_bucket_sync)


def _store_sync(key: str, content: bytes) -> None:
    _client().put_object(
        get_settings().minio_bucket_artifacts,
        key,
        io.BytesIO(content),
        length=len(content),
        content_type="application/octet-stream",
    )


async def store_artifact(key: str, content: bytes) -> None:
    await anyio.to_thread.run_sync(_store_sync, key, content)


def _fetch_sync(key: str) -> bytes:
    response = _client().get_object(get_settings().minio_bucket_artifacts, key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


async def fetch_artifact(key: str) -> bytes:
    return await anyio.to_thread.run_sync(_fetch_sync, key)
