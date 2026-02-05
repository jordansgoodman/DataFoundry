$ErrorActionPreference = "Stop"

if (!(Test-Path ".env")) {
  Write-Host "No .env found. Generating defaults..."
  & python scripts/setup/generate_env.py
}

Write-Host "Windows host detected. Skipping Ansible host setup."
Write-Host "Ensure Docker Desktop is installed and running (WSL2 backend recommended)."

# Bring up stack
& docker compose -f docker-compose.yml up -d

# First-run Superset init
if (!(Test-Path "data/.superset_initialized")) {
  Write-Host "Initializing Superset..."
  & docker compose -f docker-compose.yml run --rm superset-web /app/scripts/init.sh
  New-Item -ItemType File -Path "data/.superset_initialized" | Out-Null
}

if (!(Test-Path "data/.airflow_initialized")) {
  Write-Host "Waiting for Airflow..."
  $ready = $false
  for ($i = 0; $i -lt 30; $i++) {
    try {
      & docker compose -f docker-compose.yml exec -T airflow-webserver airflow info | Out-Null
      $ready = $true
      break
    } catch {
      Start-Sleep -Seconds 5
    }
  }
  Write-Host "Triggering NYC Taxi ingest..."
  & docker compose -f docker-compose.yml exec -T airflow-webserver airflow dags unpause nyc_taxi_full_refresh | Out-Null
  & docker compose -f docker-compose.yml exec -T airflow-webserver airflow dags trigger nyc_taxi_full_refresh | Out-Null
  New-Item -ItemType File -Path "data/.airflow_initialized" | Out-Null
}

Write-Host "DataFoundry is up."
