# Retention Policy

## Logs
- Loki retention: 7 days (configurable in `scripts/logging/loki-config.yml`)
- Prometheus retention: 15 days (configurable in `docker-compose.yml`)

## Backups
- Default retention: 7 days
- Configurable via `BACKUP_RETENTION_DAYS`

## Data
- Warehouse tables are retained indefinitely by default.
- Add partitioning or pruning if required by policy.
