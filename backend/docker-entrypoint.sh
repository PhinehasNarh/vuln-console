#!/bin/sh
set -e

case "$1" in
  api)
    alembic upgrade head
    if [ -n "$VULNCONSOLE_SEED_ADMIN_PASSWORD" ]; then
      VULNCONSOLE_USER_PASSWORD="$VULNCONSOLE_SEED_ADMIN_PASSWORD" \
        python -m vulnconsole.platform.cli create-user \
          --username admin --role admin --if-not-exists
    fi
    exec uvicorn vulnconsole.platform.api:app --host 0.0.0.0 --port 8000
    ;;
  worker)
    exec python -m vulnconsole.platform.worker
    ;;
  *)
    exec "$@"
    ;;
esac
