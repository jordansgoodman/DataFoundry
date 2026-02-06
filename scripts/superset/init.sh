#!/usr/bin/env bash
set -euo pipefail

# Ensure only one initializer runs at a time
LOCK_FILE="/app/superset_home/.init.lock"
mkdir -p /app/superset_home

exec 9>"$LOCK_FILE"
flock -x 9

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
