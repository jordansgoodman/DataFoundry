#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f .env ]]; then
  echo "Missing .env. Copy .env.example to .env and fill in values."
  exit 1
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

echo "DataFoundry is up."
