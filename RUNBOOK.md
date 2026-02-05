# DataFoundry Runbook

## When An Alert Fires
1. Check Grafana dashboards (Logs + System Metrics).
2. Check container health:
   - `docker compose ps`
3. Check service logs:
   - `docker compose logs -f --tail=200 <service>`

## Common Alerts
### High CPU / Memory
- Verify no runaway queries in Superset.
- Check Airflow task backlog.
- Consider scaling resources or reducing concurrency.

### Disk Usage
- Check `./data` and `./backups` size.
- Prune old backups or increase disk.

### Airflow Task Failures
- Open Airflow UI and inspect the failed task.
- Review logs for the task.
- Re-run the DAG if transient.

### Target Down
- Verify container health for the target.
- Restart the service if needed.

## Restore Procedure (Postgres)
1. Stop dependent services if necessary.
2. Run restore:
   - `./scripts/backup/postgres_restore.sh <backup.sql.gz>`
3. Restart the stack:
   - `docker compose up -d`
