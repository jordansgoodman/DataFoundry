# Disaster Recovery (Single Node)

## Assumptions
- You have access to the latest Postgres backup.
- You have the `.env` used for the deployment.

## Rebuild Steps
1. Provision a new Linux host with Docker.
2. Clone the repo and copy `.env`.
3. Restore backups:
   - `./scripts/backup/postgres_restore.sh <backup.sql.gz>`
4. Start the stack:
   - `./bootstrap.sh`
5. Run smoke tests:
   - `./scripts/healthcheck/smoke_test.sh`

## Verification
- Superset UI loads
- Airflow UI loads
- Grafana UI loads
- Data present in Postgres
