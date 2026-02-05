#!/usr/bin/env bash
set -euo pipefail

KEEP_ENV=false

if [[ "${1:-}" == "--keep-env" ]]; then
  KEEP_ENV=true
fi

cat <<'WARN'
This will:
- Stop all containers
- Delete ./data
- Remove .env and data/credentials.txt (unless --keep-env)
- Re-run bootstrap
WARN

echo -n "Type 'reset' to continue: "
read -r CONFIRM

if [[ "$CONFIRM" != "reset" ]]; then
  echo "Aborted."
  exit 1
fi

docker compose down
rm -rf data

if [[ "$KEEP_ENV" == "false" ]]; then
  rm -f .env data/credentials.txt
fi

./bootstrap.sh
