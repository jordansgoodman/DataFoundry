#!/usr/bin/env bash
set -euo pipefail

AF_DB="${AIRFLOW_DB:-airflow}"

create_db() {
  local db="$1"
  if psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" -tAc "SELECT 1 FROM pg_database WHERE datname='${db}'" | grep -q 1; then
    echo "Database ${db} already exists"
  else
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" -c "CREATE DATABASE \"${db}\";"
    echo "Created database ${db}"
  fi
}

create_db "$AF_DB"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" -d "$POSTGRES_DB" <<SQL
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'analytics') THEN
    CREATE ROLE analytics LOGIN PASSWORD 'change_me';
  END IF;
END$$;

CREATE SCHEMA IF NOT EXISTS analytics AUTHORIZATION CURRENT_USER;
SQL
