# Operator Guide

Running and caring for the console in a homelab. Kubernetes guidance arrives in Milestone 8.

## First start

```bash
cd deploy/compose
cp .env.example .env    # then change EVERY value; .env is gitignored
docker compose up -d
docker compose ps       # wait for all services healthy
```

Setting `VULNCONSOLE_SEED_ADMIN_PASSWORD` in `.env` before first start creates the `admin` account automatically. Create further accounts from inside the api container:

```bash
docker compose exec -e VULNCONSOLE_USER_PASSWORD='a-strong-password' api \
  python -m vulnconsole.platform.cli create-user --username sana --role security-engineer
```

Roles: `admin`, `security-engineer`, `developer`, `viewer`. CI systems should never get a user account; mint an ingestion-only API token instead (POST `/api/v1/auth/api-tokens` as admin) and treat the returned `vc_...` value as a secret; it is shown exactly once.

## Service map

| Service | Purpose | Data volume |
|---------|---------|-------------|
| traefik | the only exposed entrypoint (:80/:443) | none |
| api | REST API, runs migrations on boot | none |
| worker | parse/normalize pipeline | none |
| frontend | static SPA | none |
| postgres | system of record | postgres-data |
| minio | raw uploaded reports | minio-data |
| nats | event streams | nats-data |
| redis | cache, rate limits | redis-data |
| opensearch | search (used from M2) | opensearch-data |
| prometheus, grafana | metrics and dashboards | prometheus-data, grafana-data |

## Health

- Liveness: `GET /healthz` on the api; readiness with per-dependency detail: `GET /readyz` (checks postgres, nats, redis).
- `docker compose ps` shows healthcheck state for every service; `docker compose logs <service>` for structured JSON logs.
- A scan stuck in `received` means the worker is down or NATS is unreachable; `failed` scans carry the reason in their `error` field (`GET /api/v1/scans?status=failed`).

## Backups

Everything of record lives in two places: **postgres-data** (all findings, users, audit) and **minio-data** (raw artifacts). Snapshot both; OpenSearch and Redis are rebuildable caches. Minimal routine:

```bash
docker compose exec postgres pg_dump -U vulnconsole -Fc vulnconsole > backup-$(date +%F).dump
# minio: snapshot the named volume or mirror the bucket with `mc mirror`
```

Restore drill: fresh volumes, `docker compose up -d postgres`, `pg_restore`, start the rest. Practice this before you need it.

## Upgrades

```bash
git pull
docker compose build api worker frontend
docker compose up -d      # api re-runs alembic migrations on boot
```

Migrations are forward-only in practice; take a postgres dump first.

## Security posture (current, homelab)

Accepted deviations and their exit plans are tracked in [security/threat-model.md](security/threat-model.md): OpenSearch security plugin disabled, no internal TLS, secrets in `.env`. Do not expose anything but Traefik beyond localhost, and put TLS certificates on Traefik before letting the console leave your LAN. Rotate `JWT_SECRET_KEY` to invalidate all sessions.
