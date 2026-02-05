$ErrorActionPreference = "Stop"

if (!(Test-Path ".env")) {
  Write-Host "Missing .env. Copy .env.example to .env and fill in values."
  exit 1
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

Write-Host "DataFoundry is up."
