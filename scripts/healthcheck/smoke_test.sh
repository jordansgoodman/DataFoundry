#!/usr/bin/env bash
set -euo pipefail

HOST="${HOST:-localhost}"
BASE="http://${HOST}"

check() {
  local name="$1"
  local url="$2"
  if curl -fsS "$url" >/dev/null; then
    echo "[OK] $name"
  else
    echo "[FAIL] $name"
    exit 1
  fi
}

check "NGINX" "${BASE}/"
check "BI" "${BASE}/bi/"
check "Airflow" "${BASE}/airflow/"
check "Grafana" "${BASE}/grafana/"

if docker compose exec -T postgres pg_isready -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" >/dev/null; then
  echo "[OK] Postgres"
else
  echo "[FAIL] Postgres"
  exit 1
fi

echo "Smoke test complete."
