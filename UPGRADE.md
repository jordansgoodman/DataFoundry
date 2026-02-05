# Upgrade Guide

## Goals
- Safe, repeatable upgrades
- Minimal downtime

## Before You Upgrade
- Take a Postgres backup:
  - `./scripts/backup/postgres_backup.sh`
- Note your current image tags in `docker-compose.yml`.

## Upgrade Steps
1. Pull new images:
   - `docker compose pull`
2. Restart the stack:
   - `docker compose up -d`
3. Verify health:
   - `docker compose ps`
   - Check `/superset/`, `/airflow/`, `/grafana/`

## Rollback
- Revert image tags in `docker-compose.yml` and re-run `docker compose up -d`.
- Restore the DB if necessary:
  - `./scripts/backup/postgres_restore.sh <backup.sql.gz>`
