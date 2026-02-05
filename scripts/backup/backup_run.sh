#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"

./scripts/backup/postgres_backup.sh

# Retention cleanup
find "$BACKUP_DIR" -type f -name "postgres_*.sql.gz" -mtime "+${RETENTION_DAYS}" -print -delete
