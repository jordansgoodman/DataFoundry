$ErrorActionPreference = "Stop"

if (!(Test-Path ".env")) {
  Write-Host "No .env found. Generating defaults..."
  & python scripts/setup/generate_env.py
}
if (Test-Path ".env") {
  $envMap = @{}
  Get-Content .env | ForEach-Object {
    if ($_ -and ($_ -notmatch '^#') -and ($_ -match '=')) {
      $parts = $_.Split('=', 2)
      $envMap[$parts[0]] = $parts[1]
    }
  }
  New-Item -ItemType Directory -Force -Path "data/pgadmin" | Out-Null
  $servers = @"
{
  "Servers": {
    "1": {
      "Name": "DataFoundry Postgres",
      "Group": "Servers",
      "Host": "postgres",
      "Port": 5432,
      "MaintenanceDB": "$($envMap['POSTGRES_DB'])",
      "Username": "$($envMap['POSTGRES_USER'])",
      "SSLMode": "prefer"
    }
  }
}
"@
  $servers | Out-File -FilePath "data/pgadmin/servers.json" -Encoding utf8
  "$('postgres'):5432:$($envMap['POSTGRES_DB']):$($envMap['POSTGRES_USER']):$($envMap['POSTGRES_PASSWORD'])" | Out-File -FilePath "data/pgadmin/pgpass" -Encoding ascii
}

Write-Host "Windows host detected. Skipping Ansible host setup."
Write-Host "Ensure Docker Desktop is installed and running (WSL2 backend recommended)."

# Bring up stack
& docker compose -f docker-compose.yml up -d

# First-run Superset init
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
