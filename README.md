# DataFoundry

Local-first, self-hosted analytics stack with one-command install.

## What this is
- Single-node analytics appliance
- Docker Compose runtime
- Opinionated defaults, minimal config

## Core Principles
- Local-only, no cloud dependencies
- Fully open source
- Infrastructure as code
- Opinionated defaults
- Minimal configuration surface
- One-command install
- Idempotent and repeatable
- Designed for 100–1000+ business users on a single node

## Platform Components
- PostgreSQL: analytics warehouse and metadata store
- Separate metadata database for Airflow (default: `airflow`)
- DataFoundry BI (Streamlit): BI and dashboards
- Airflow: orchestration and scheduling
- Redis: caching and async coordination
- NGINX: reverse proxy and single-URL routing
- dlt: ingestion pipelines (containerized)
- Grafana: observability UI
- Loki + Promtail: log aggregation
- Prometheus + Node Exporter: system metrics
- StatsD Exporter: Airflow metrics bridge

## Quick start
1. Run the bootstrap for your OS (it auto-generates `.env` and credentials on first run):
   - Linux/macOS: `./bootstrap.sh`
   - Windows (PowerShell): `./bootstrap.ps1`

The bootstrap script brings up services and runs first-run initialization (Docker and Python 3 must already be installed).

## Data Ingestion (dlt + Airflow)
The Airflow DAG `nyc_taxi_full_refresh` uses dlt to load NYC Taxi data into Postgres.

Trigger it after the stack is up:
- `docker compose exec airflow-webserver airflow dags trigger nyc_taxi_full_refresh`

## Logging And Observability
This stack includes Grafana + Loki + Promtail for local log aggregation.

- Grafana: `http://<host>/grafana/` (defaults in `.env.example`)
- Logs flow: Docker containers -> Promtail -> Loki -> Grafana
- Services are labeled with `logging=promtail` so Promtail only ingests those containers.
- Dashboards: `DataFoundry Logs` and `DataFoundry Logs Overview`

## System Metrics
System metrics are collected with Prometheus + Node Exporter and visualized in Grafana.
The “DataFoundry System Metrics” dashboard is auto-provisioned.
Alert rules for CPU, memory, disk, and node exporter are included in Prometheus.

## Airflow Alerts
Airflow emits StatsD metrics which are scraped by Prometheus via `statsd-exporter`.
Alerts trigger when task failures occur.

## Alert Routing (Slack-ready)
Prometheus sends alerts to Alertmanager. A Slack receiver template is included.
To enable Slack:
- Edit `scripts/metrics/alertmanager/alertmanager.yml` and replace the webhook URL.
- Set the Slack channel name (default: `#datafoundry-alerts`).
- Restart Alertmanager: `docker compose up -d alertmanager`
- Trigger a test by stopping node-exporter briefly and confirm Slack alerts arrive.

## Single URL Access
All UIs are routed through NGINX:

- BI: `http://<host>:8080/bi/`
- Airflow: `http://<host>:8080/airflow/`
- Grafana: `http://<host>:8080/grafana/`
- pgAdmin: `http://<host>:8080/pgadmin/`

## DB Tools
pgAdmin is pre-configured with the Postgres server and password on first boot.
Credentials are available in `data/credentials.txt`.

## DataFoundry BI
The BI app is powered by Streamlit and provides:
- SQL Lab (run queries)
- Saved queries
- Dashboards
- RBAC (Admin/Analyst/Viewer)
- Scheduled refreshes (via `bi-worker`)
- Audit logs
- Multi‑tenant workspaces
- Multi‑datasource metadata layer
- Chart library and dashboard builder (layouts + filters)

Make sure `.env` sets:
- `BI_BASE_URL=http://<host>:8080/bi`
- `AIRFLOW__WEBSERVER__BASE_URL=http://<host>:8080/airflow`

## Detailed Setup Flow
This is what happens when you run the bootstrap:

1. Generates `.env` if missing (writes credentials to `data/credentials.txt`)
2. Verifies Docker is installed and running
3. Creates persistent data directories under `./data`
4. Starts the Docker Compose stack
5. Leaves the stack running behind NGINX

On macOS/Windows, the bootstrap assumes Docker Desktop is already running.

## First-Run Behavior
On first install, the system:
- Creates Postgres volumes
- Initializes Postgres schemas and roles
- Triggers the NYC Taxi ingestion DAG once

## Service Map
Services are all on the internal Docker network `df` and exposed only via NGINX.

- `nginx`: edge routing and reverse proxy
- `postgres`: analytics warehouse
- `redis`: cache and task queue
- `bi`: DataFoundry BI (Streamlit)
- `bi-worker`: scheduled query runner for BI refreshes
- `airflow-webserver`: Airflow UI
- `airflow-scheduler`: Airflow scheduler
- `airflow-worker`: Airflow Celery worker
- `dlt`: ingestion tooling container
- `loki`: log store
- `promtail`: log shipper
- `grafana`: logs and metrics UI
- `pgadmin`: PostgreSQL admin UI
- `prometheus`: metrics store
- `node-exporter`: host metrics
- `statsd-exporter`: Airflow metrics bridge

## Testing On Ubuntu VM (from macOS)
Once you are inside the Ubuntu VM:

1. Update packages:
   - `sudo apt-get update`
2. Install basics:
   - `sudo apt-get install -y git python3 python3-pip`
3. Clone the repo:
   - `git clone <your-repo-url> DataFoundry`
4. Go to the repo:
   - `cd DataFoundry`
5. Run the installer:
   - `./bootstrap.sh`
6. Trigger the NYC Taxi load:
   - `docker compose exec airflow-webserver airflow dags trigger nyc_taxi_full_refresh`
7. Open services:
   - BI: `http://<vm-ip>:8080/bi/`
   - Airflow: `http://<vm-ip>:8080/airflow/`

## Defaults
On first run, `.env` is generated automatically with strong random defaults.
Credentials are written to `data/credentials.txt`.

## Backups And Restore
- Backup Postgres:
  - `./scripts/backup/postgres_backup.sh`
- Restore Postgres:
  - `./scripts/backup/postgres_restore.sh <backup.sql.gz>`
- Scheduled backup (cron):
- `./scripts/backup/backup_run.sh` (uses `BACKUP_RETENTION_DAYS`, default 7)
- Cron example: `scripts/backup/backup_cron.example`
- Systemd example: `scripts/backup/datafoundry-backup.service` + `scripts/backup/datafoundry-backup.timer`

## Upgrades
See `UPGRADE.md` for a safe upgrade and rollback process.

## Security Hardening
See `scripts/security/README.md` for TLS and access control guidance.

## SSO
See `scripts/security/SSO.md` for OIDC/OAuth guidance.

## Governance
See `GOVERNANCE.md` for role guidance and access policies.

## Runbook
See `RUNBOOK.md` for incident response steps.

## Smoke Tests
- `./scripts/healthcheck/smoke_test.sh` checks key endpoints and Postgres.

## Reset (Dev Only)
- `./reset.sh` wipes `./data` and reboots the stack
- `./reset.sh --keep-env` preserves `.env` and credentials

## Go-Live
See `GO_LIVE.md` for a production cutover checklist.

## Backup Verification
- `./scripts/backup/backup_verify.sh <backup.sql.gz>`

## Capacity Testing
See `LOAD_TEST.md` for a suggested load-testing plan.

## Retention Policy
See `RETENTION.md` for log, metrics, and backup retention guidance.

## Disaster Recovery
See `DISASTER_RECOVERY.md` for rebuild and restore steps.

## Cross-Platform Notes
- Linux/macOS: requires Docker installed locally.
- Windows: use `bootstrap.ps1` in PowerShell (Docker Desktop required).
- Optional: `make up`, `make down`, `make logs`, `make init` for common tasks.

## Structure
- `bootstrap.sh` one-command installer
- `docker-compose.yml` runtime services
- `docker-compose.override.yml.example` optional resource limits
- `scripts/` init and bootstrap helpers
- `scripts/dlt/` data ingestion pipelines

## Configuration Summary
All user configuration is provided via `.env`.
Only essential values are exposed and everything else uses opinionated defaults.

Key variables:
- `DF_HOSTNAME`
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `AIRFLOW_DB`
- `BI_ADMIN_USERNAME`, `BI_ADMIN_PASSWORD`, `BI_BASE_URL`, `BI_SCHEDULER_POLL_SECONDS`, `BI_DASHBOARD_CACHE_TTL_SECONDS`
- `AIRFLOW_ADMIN_USERNAME`, `AIRFLOW_ADMIN_PASSWORD`, `AIRFLOW_ADMIN_EMAIL`
- `AIRFLOW__CORE__FERNET_KEY`, `AIRFLOW__WEBSERVER__BASE_URL`, `AIRFLOW__WEBSERVER__WEB_SERVER_URL_PREFIX`
- `AIRFLOW_UID`
- `REDIS_PASSWORD`
- `GRAFANA_ADMIN_USER`, `GRAFANA_ADMIN_PASSWORD`
- `NYC_TAXI_URL`

## Resource Sizing (Single Node)
Recommended starting point:
- 4 vCPU / 16 GB RAM / 200+ GB disk for pilot usage
- 8 vCPU / 32 GB RAM / 500+ GB disk for heavier analytics

## Resource Limits (Optional)
To enforce container limits, copy `docker-compose.override.yml.example` to `docker-compose.override.yml`
and adjust values for your environment.

## Notes
- All analytics tooling runs in containers.

## Production Readiness Checklist
- [ ] Store `data/credentials.txt` securely and rotate credentials if needed
- [ ] Rotate autogenerated secrets before production use
- [ ] Enable TLS in NGINX and install certificates
- [ ] Configure IP allowlist or SSO
- [ ] Configure Alertmanager Slack webhook
- [ ] Verify backups run and retention is configured
- [ ] Run `./scripts/healthcheck/smoke_test.sh`
- [ ] Run a backup verification test
- [ ] Confirm dashboards load and refresh
- [ ] Validate restore procedure in a staging environment
