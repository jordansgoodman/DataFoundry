#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f .env ]]; then
  echo "No .env found. Generating defaults..."
  python3 scripts/setup/generate_env.py
fi

if ! grep -q "^AIRFLOW_UID=" .env; then
  echo "AIRFLOW_UID=$(id -u)" >> .env
fi
if ! grep -q "^AIRFLOW__WEBSERVER__WEB_SERVER_URL_PREFIX=" .env; then
  echo "AIRFLOW__WEBSERVER__WEB_SERVER_URL_PREFIX=/airflow" >> .env
fi
if ! grep -q "^AIRFLOW__WEBSERVER__BASE_URL=" .env; then
  echo "AIRFLOW__WEBSERVER__BASE_URL=http://localhost:8080/airflow" >> .env
fi

ensure_permissions() {
  mkdir -p data
  if [[ "$(id -u)" -eq 0 ]]; then
    chmod -R a+rwX data || true
  elif command -v sudo >/dev/null 2>&1; then
    sudo chmod -R a+rwX data || true
  else
    chmod -R a+rwX data || true
  fi
}

mkdir -p \
  data/airflow \
  data/postgres \
  data/redis \
  data/logging/loki \
  data/logging/promtail \
  data/logging/grafana \
  data/metrics/prometheus \
  data/metrics/alertmanager \
  data/pgadmin

echo "Fixing data directory permissions..."
ensure_permissions

./scripts/pgadmin/bootstrap_pgadmin.sh

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker not found. Install Docker Engine (Linux) or Docker Desktop."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon is not running. Start Docker and try again."
  exit 1
fi

docker compose -f docker-compose.yml up -d

# First-run Airflow ingest
if [[ ! -f data/.airflow_initialized ]]; then
  echo "Waiting for Airflow..."
  for i in {1..30}; do
    if docker compose -f docker-compose.yml exec -T airflow-webserver airflow info >/dev/null 2>&1; then
      break
    fi
    sleep 5
  done
  echo "Triggering NYC Taxi ingest..."
  docker compose -f docker-compose.yml exec -T airflow-webserver airflow dags unpause nyc_taxi_full_refresh || true
  docker compose -f docker-compose.yml exec -T airflow-webserver airflow dags trigger nyc_taxi_full_refresh || true
  touch data/.airflow_initialized
fi

echo "DataFoundry is up."
