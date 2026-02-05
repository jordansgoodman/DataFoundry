#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: ./scripts/backup/postgres_restore.sh <backup.sql.gz>"
  exit 1
fi

BACKUP_FILE="$1"

gunzip -c "$BACKUP_FILE" | docker compose exec -T postgres psql -U "${POSTGRES_USER}" "${POSTGRES_DB}"

echo "Restore complete"
