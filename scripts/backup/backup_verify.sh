#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: ./scripts/backup/backup_verify.sh <backup.sql.gz>"
  exit 1
fi

BACKUP_FILE="$1"

# Create temp db, restore, and run a simple check
TMP_DB="verify_$(date +%s)"

docker compose exec -T postgres psql -U "${POSTGRES_USER}" -c "CREATE DATABASE ${TMP_DB};"

gunzip -c "$BACKUP_FILE" | docker compose exec -T postgres psql -U "${POSTGRES_USER}" "${TMP_DB}"

# Basic check: table exists
if docker compose exec -T postgres psql -U "${POSTGRES_USER}" -d "${TMP_DB}" -c "\dt analytics.*" | grep -q "nyc_taxi"; then
  echo "[OK] Backup verification passed"
else
  echo "[FAIL] Backup verification failed"
fi

# Cleanup
docker compose exec -T postgres psql -U "${POSTGRES_USER}" -c "DROP DATABASE ${TMP_DB};"
