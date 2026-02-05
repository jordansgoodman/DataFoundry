#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f .env ]]; then
  echo ".env not found"
  exit 1
fi

set -a
source .env
set +a

mkdir -p data/pgadmin

cat > data/pgadmin/servers.json <<JSON
{
  "Servers": {
    "1": {
      "Name": "DataFoundry Postgres",
      "Group": "Servers",
      "Host": "postgres",
      "Port": 5432,
      "MaintenanceDB": "${POSTGRES_DB}",
      "Username": "${POSTGRES_USER}",
      "SSLMode": "prefer"
    }
  }
}
JSON

cat > data/pgadmin/pgpass <<PGPASS
postgres:5432:${POSTGRES_DB}:${POSTGRES_USER}:${POSTGRES_PASSWORD}
PGPASS

chmod 600 data/pgadmin/pgpass

