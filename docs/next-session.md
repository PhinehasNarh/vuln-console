# Next Session Runbook: Milestone 1 Verification

Written 2026-07-02. Everything below is code-complete and unit-tested; the live end-to-end run was deferred because the first infra image pull was slow. This is the exact script for finishing verification.

## What is already done

- M0: full architecture package (13 ADRs, domain model, decomposition, threat model, roadmap, diagrams), monorepo scaffold, CI.
- M1 backend: shared kernel, identity (JWT auth, RBAC, API tokens, audit), ingestion (SARIF connector, MinIO artifacts, scan lifecycle), normalization (fingerprint v1, canonical findings, keyset-paginated findings API), NATS worker, Alembic migration, CLI.
- M1 frontend: Ledger design language (docs/design/), workspace shell with command bar, findings table, inspector panel, command palette (Ctrl+K), keyboard navigation, upload sheet, dark/light themes.
- Verified so far: 16/16 unit tests pass; pyflakes clean; frontend `tsc --noEmit` clean; `vite build` succeeds; all three app images build; compose config validates.
- Secrets: `deploy/compose/.env` exists (gitignored) with generated credentials, including `VULNCONSOLE_SEED_ADMIN_PASSWORD` (the admin login password).

## Machine quirks discovered (do not rediscover these)

1. **Windows App Control blocks unsigned native binaries** in the venv: `ruff.exe` and mypy's compiled core cannot run locally. They run in CI on Linux instead. Local fallback: `python -m pyflakes`.
2. **The `&` in the `L&D` folder name breaks `npm run` / `npx`** (cmd.exe parses it). Invoke tools directly instead:
   `node node_modules/typescript/bin/tsc --noEmit` and `node node_modules/vite/bin/vite.js build`.
3. Docker Desktop must be started manually before compose commands.

## Step 1: start the application

```bash
cd "deploy/compose"
docker compose up -d          # first run finishes pulling infra images
docker compose ps             # repeat until every service is healthy (opensearch is slowest)
```

Then open:

| What | URL |
|------|-----|
| Web UI | http://localhost |
| API docs (OpenAPI) | http://localhost/api/v1/docs |
| Grafana | http://localhost:3000 |
| MinIO console | http://localhost:9001 |

Log in to the UI as `admin` with the `VULNCONSOLE_SEED_ADMIN_PASSWORD` value from `deploy/compose/.env`.

## Step 2: UI acceptance walkthrough

1. Sign in. Empty state should read "No findings match this view."
2. Press `Ctrl+K`, run "Upload scan report" (or click upload report), repository `demo/app`, file `deploy/sample-data/semgrep-example.sarif`.
3. Within a few seconds (worker pipeline), refresh via the palette or toolbar: exactly **2 findings** appear: one critical (SQL injection) and one medium (hardcoded password). The SARIF contains 3 results; two share rule + file, proving dedup.
4. Upload the same file again: still **2 findings** (acceptance criterion: no duplicates). Open the critical finding: the inspector's "source scans" list shows **4 entries** for it (2 results x 2 uploads), 6 across both findings.
5. Keyboard pass: `/` focuses search, `j`/`k` move selection, `Esc` closes the inspector, `Ctrl+K` opens the palette, theme toggle works, focus rings visible when tabbing.

## Step 3: API acceptance (curl)

```bash
PASS=$(grep VULNCONSOLE_SEED_ADMIN_PASSWORD deploy/compose/.env | cut -d= -f2)
TOKEN=$(curl -s -X POST http://localhost/api/v1/auth/token \
  -d "username=admin&password=$PASS" | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# 401 without a token, problem+json shape
curl -si http://localhost/api/v1/findings | head -3

# upload, then list
curl -s -X POST http://localhost/api/v1/scans \
  -H "Authorization: Bearer $TOKEN" \
  -F repository=demo/api -F file=@deploy/sample-data/semgrep-example.sarif
curl -s "http://localhost/api/v1/findings?repository=demo/api" -H "Authorization: Bearer $TOKEN"
```

## Step 4: RBAC and audit checks

```bash
# viewer role cannot ingest (expect 403 problem+json)
docker compose -f deploy/compose/docker-compose.yml exec -e VULNCONSOLE_USER_PASSWORD=viewer-test-password api \
  python -m vulnconsole.platform.cli create-user --username viewer --role viewer
# then log in as viewer and POST /api/v1/scans: expect 403

# audit trail exists
docker compose -f deploy/compose/docker-compose.yml exec postgres \
  psql -U vulnconsole -d vulnconsole -c \
  "SELECT action, actor, created_at FROM identity.audit_events ORDER BY created_at DESC LIMIT 10;"
```

## Step 5: integration test suite

Ports are loopback-bound, so the tests reach compose services directly. From `backend/`:

```bash
source deploy/compose/.env  # or read the values manually
export DATABASE_URL="postgresql+asyncpg://vulnconsole:$POSTGRES_PASSWORD@localhost:5432/vulnconsole"
export REDIS_URL="redis://:$REDIS_PASSWORD@localhost:6379/0"
export MINIO_SECRET_KEY="$MINIO_ROOT_PASSWORD"
export JWT_SECRET_KEY="$JWT_SECRET_KEY"
INTEGRATION=1 ./.venv/Scripts/python.exe -m pytest tests/integration -q
```

(The schema is already migrated because the api container ran `alembic upgrade head` on start.)

## Step 6: worker resilience glance

```bash
docker compose -f deploy/compose/docker-compose.yml logs worker | tail -30
# expect scan.parsed / scan.normalized log lines, no worker.giving_up entries
```

## Step 7: push-triggered CI

CI on GitHub runs: typography (dash ban), compose config validation, ruff, backend unit tests, frontend typecheck + build, and an advisory mypy job (mypy cannot run on this machine, see quirks). Confirm all green on the repo's Actions tab.

## If something fails

- `api` unhealthy: `docker compose logs api`; first suspect is migration or NATS connection; `/readyz` reports per-dependency checks.
- OpenSearch restart loop: raise Docker Desktop memory (needs ~1 GB free for the 512 MB heap).
- Frontend 404 on /api: Traefik router priorities; `docker compose logs traefik`.
- Findings never appear: `docker compose logs worker`; the scan row's `status`/`error` columns (`GET /api/v1/scans`) say which stage failed.

## Step 8: Milestone 2 correlation checks (added later on 2026-07-02)

Four more connectors and fingerprint v2 landed after this runbook was first written (32 unit tests cover them, including cross-scanner correlation proofs). Live checks:

1. Upload `deploy/sample-data/trivy-example.json` AND `deploy/sample-data/grype-example.json` to the **same repository**: CVE-2024-35195 in `requests` must appear as **one finding** whose inspector shows both `trivy` and `grype` under "reported by", with package and fixed-in version populated.
2. Upload `deploy/sample-data/gitleaks-example.json` AND `deploy/sample-data/trufflehog-example.jsonl` to the same repository: the AWS key in `config/prod.env` must be **one finding** reported by both tools.
3. Confirm redaction end to end: `GET /api/v1/scans` then inspect a secret scan's raw findings in the DB; `SELECT payload FROM ingestion.raw_findings WHERE finding_class = 'secret';` must contain `[REDACTED]` and never a plaintext secret.
4. `?cve=CVE-2024-35195` filter on `/api/v1/findings` returns exactly the correlated finding.

(The api container runs migration 0002 automatically on start.)

## After verification passes

1. Remove the "not yet live-tested" note from README.md.
2. Tick M1 acceptance criteria in docs/roadmap.md.
3. Start Milestone 2 (connector expansion + fingerprint v2 + OpenSearch search); backlog in the roadmap.
