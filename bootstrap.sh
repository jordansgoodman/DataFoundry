#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f .env ]]; then
  echo "No .env found. Generating defaults..."
  python3 scripts/setup/generate_env.py
fi

OS_NAME="$(uname -s)"

if [[ "$OS_NAME" == "Linux" ]]; then
  if ! command -v ansible-playbook >/dev/null 2>&1; then
    echo "Installing ansible..."
    python3 -m pip install --user ansible
    export PATH="$HOME/.local/bin:$PATH"
  fi
  ansible-playbook -i "localhost," -c local ansible/site.yml
else
  echo "Non-Linux host detected ($OS_NAME). Skipping Ansible host setup."
  echo "Use ./bootstrap-dev.sh on macOS/Windows for the Docker-only path."
  echo "Ensure Docker Desktop is installed and running."
fi

# First-run Superset init
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
