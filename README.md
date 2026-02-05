# DataFoundry

Local-first, self-hosted analytics stack with one-command install.

## What this is
- Single-node analytics appliance
- Docker Compose runtime
- Ansible-managed host setup
- Opinionated defaults, minimal config

## Quick start
1. Copy `.env.example` to `.env` and fill in values.
2. Run `./bootstrap.sh`.

The bootstrap script installs Docker (via Ansible), brings up services, and runs first-run initialization.

## Data Ingestion (dlt + Airflow)
The Airflow DAG `nyc_taxi_full_refresh` uses dlt to load NYC Taxi data into Postgres
and then auto-registers the dataset in Superset.

Trigger it after the stack is up:
- `docker compose exec airflow-webserver airflow dags trigger nyc_taxi_full_refresh`

## Logging And Observability
This stack includes Grafana + Loki + Promtail for local log aggregation.

- Grafana: `http://<host>/grafana/` (defaults in `.env.example`)
- Logs flow: Docker containers -> Promtail -> Loki -> Grafana
- Services are labeled with `logging=promtail` so Promtail only ingests those containers.

## Single URL Access
All UIs are routed through NGINX:

- Superset: `http://<host>/superset/`
- Airflow: `http://<host>/airflow/`
- Grafana: `http://<host>/grafana/`

Make sure `.env` sets:
- `SUPERSET_BASE_URL=http://<host>/superset`
- `AIRFLOW__WEBSERVER__BASE_URL=http://<host>/airflow`

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
5. Create `.env`:
   - `cp .env.example .env`
   - Edit `.env` and set secrets.
6. Run the installer:
   - `./bootstrap.sh`
7. Trigger the NYC Taxi load:
   - `docker compose exec airflow-webserver airflow dags trigger nyc_taxi_full_refresh`
8. Open services:
   - Superset: `http://<vm-ip>/superset/`
   - Airflow: `http://<vm-ip>/airflow/`

## Defaults
This repo ships with development-friendly defaults in `.env.example` (admin creds, passwords, secret keys).
Change them before using this in any real environment.

## Structure
- `bootstrap.sh` one-command installer
- `ansible/` host configuration and deploy
- `docker-compose.yml` runtime services
- `scripts/` init and bootstrap helpers
- `scripts/dlt/` data ingestion pipelines

## Notes
- Host Python is used only for Ansible.
- All analytics tooling runs in containers.
