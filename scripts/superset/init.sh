#!/usr/bin/env bash
set -euo pipefail

# Ensure only one initializer runs at a time
LOCK_FILE="/tmp/superset-init.lock"

exec 9>"$LOCK_FILE"
flock -x 9

echo "Waiting for Postgres..."
for i in {1..60}; do
  if pg_isready -h postgres -p 5432 >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

superset db upgrade
superset fab create-admin \
  --username "${SUPERSET_ADMIN_USERNAME}" \
  --firstname Admin \
  --lastname User \
  --email "${SUPERSET_ADMIN_EMAIL}" \
  --password "${SUPERSET_ADMIN_PASSWORD}" || true

superset init

if [[ -f /app/scripts/bootstrap.sh ]]; then
  /app/scripts/bootstrap.sh
fi
