# Developer Guide

How to work on the console. Assumes Python 3.12, Node 22+, and Docker.

## Repository layout

```
backend/           Python modular monolith
  src/vulnconsole/
    shared/        kernel: config, db, events, security, problems, pagination
    contexts/      bounded contexts; each has domain/ application/ api/ infrastructure/
    platform/      composition roots: api (FastAPI), worker (NATS), cli
  alembic/         migrations (async env)
  tests/           unit/ (no infra needed) and integration/ (live compose stack)
frontend/          React + TypeScript + Vite SPA (design system: docs/design/)
deploy/compose/    the runnable stack; sample-data/ holds example reports
ops/               prometheus, grafana, traefik configuration
docs/              everything else you are reading
```

## Golden rules

1. **Context boundaries**: a context never imports another context's `domain` or `infrastructure`. Cross-context calls go through the other context's `application` service or NATS events. Enforced by import-linter contracts in `pyproject.toml`; CI runs `lint-imports`, and on this machine run `./.venv/Scripts/python.exe -c "from importlinter.cli import lint_imports_command; lint_imports_command()"` (the console-script exe is App Control blocked).
2. **Raw is sacred**: scanner output is stored verbatim as RawFinding; all triage state hangs off the canonical Finding (ADR-0007).
3. **Every mutation writes an AuditEvent** in the same transaction.
4. **Problem details everywhere**: raise `ProblemError` (shared/problems.py); never return ad-hoc error JSON.
5. **No em or en dashes in any file**; CI fails the build on them.

## Backend loop

```bash
cd backend
py -3.12 -m venv .venv
./.venv/Scripts/python.exe -m pip install -e '.[dev]'
./.venv/Scripts/python.exe -m pytest tests/unit -q     # fast, no infra
```

Run the API against the compose infra (postgres, redis, nats, minio up):

```bash
./.venv/Scripts/python.exe -m alembic upgrade head
./.venv/Scripts/python.exe -m uvicorn vulnconsole.platform.api:app --reload --port 8000
./.venv/Scripts/python.exe -m vulnconsole.platform.worker      # second terminal
```

Configuration comes from environment variables or a `.env` file (see `backend/src/vulnconsole/shared/config.py` for every setting and its default). Integration tests: `INTEGRATION=1 pytest tests/integration -q` (see docs/next-session.md for the env vars).

On this dev machine specifically: ruff and mypy native binaries cannot execute directly (App Control blocks unsigned executables). Two local options that both work:

- Quick: `./.venv/Scripts/python.exe -m pyflakes src/vulnconsole tests`.
- Ground truth, identical to CI (pinned versions): run the linters in Docker.

```bash
# from backend/, with Docker running
docker run --rm -v "$(pwd):/io" -w /io ghcr.io/astral-sh/ruff:0.15.20 check .
docker run --rm -v "$(pwd):/io" -w /io python:3.12-slim \
  bash -c "pip install -e '.[dev]' -q && mypy src/vulnconsole"
```

Ruff and mypy are pinned in `pyproject.toml` so Docker and CI agree exactly; bump them deliberately.

## Frontend loop

```bash
cd frontend
npm install
node node_modules/vite/bin/vite.js          # dev server on :5173, proxies /api to :8000
node node_modules/typescript/bin/tsc --noEmit
```

(Direct `node` invocation because the repo path contains `&`, which breaks npm's cmd wrapper on Windows. `npm run dev` works fine on other machines.)

Design tokens and component conventions: [design/design-language.md](design/design-language.md) and [design/ux-blueprint.md](design/ux-blueprint.md). Do not introduce colors or spacing outside the tokens in `src/styles.css`.

## Adding a scanner connector (the most common task)

1. Create `backend/src/vulnconsole/contexts/ingestion/connectors/<tool>.py` implementing the `Connector` protocol (`format_id`, `display_name`, `sniff`, `parse`) from `connectors/base.py`. Parse defensively: the artifact is untrusted input.
2. Map severities into the five-level scale; preserve the raw result dict as the draft `payload`.
3. Register it in `connectors/__init__.py` (in-tree) or via the `vulnconsole.connectors` entry-point group (external package).
4. Add a real sample report under `deploy/sample-data/` and a parse test in `tests/unit/` (see `test_sarif_connector.py` as the template).
5. Nothing else changes: upload, storage, fingerprinting, and the API pick the new format up automatically.

## Conventions

- Python: typed everywhere, `ruff` line length 100, async-first, structlog for logging (`logger.info("scan.parsed", scan_id=...)`, event-style keys).
- API: follow [api/conventions.md](api/conventions.md) exactly (pagination envelope, problem+json, versioning).
- Commits: imperative summary line; body lists what and why. New decisions get an ADR, never a rewrite of an old one.
