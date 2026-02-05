#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f .env ]]; then
  echo "Missing .env. Copy .env.example to .env and fill in values."
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker not found. Install Docker Desktop (macOS/Windows) or Docker Engine (Linux)."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon is not running. Start Docker and try again."
  exit 1
fi

docker compose -f docker-compose.yml up -d

if [[ ! -f data/.superset_initialized ]]; then
  echo "Initializing Superset..."
  docker compose -f docker-compose.yml run --rm superset-web /app/scripts/init.sh
  touch data/.superset_initialized
fi

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
