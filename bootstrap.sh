#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f .env ]]; then
  echo "Missing .env. Copy .env.example to .env and fill in values."
  exit 1
fi

if ! command -v ansible-playbook >/dev/null 2>&1; then
  echo "Installing ansible..."
  python3 -m pip install --user ansible
  export PATH="$HOME/.local/bin:$PATH"
fi

ansible-playbook -i "localhost," -c local ansible/site.yml

# First-run Superset init
if [[ ! -f data/.superset_initialized ]]; then
  echo "Initializing Superset..."
  docker compose -f docker-compose.yml run --rm superset-web /app/scripts/init.sh
  touch data/.superset_initialized
fi

# dbt run (optional)
if [[ ! -f data/.dbt_initialized ]]; then
  echo "Running dbt seed/run/test..."
  docker compose -f docker-compose.yml run --rm dbt bash -c "dbt seed && dbt run && dbt test"
  touch data/.dbt_initialized
fi

echo "DataFoundry is up."
