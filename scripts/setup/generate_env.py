import os
import secrets
import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_EXAMPLE = ROOT / ".env.example"
ENV_FILE = ROOT / ".env"
CREDS_FILE = ROOT / "data" / "credentials.txt"

DEFAULT_HOST = os.environ.get("DF_HOSTNAME", "localhost")

KEYS_TO_GEN = {
    "POSTGRES_PASSWORD": 24,
    "SUPERSET_ADMIN_PASSWORD": 24,
    "AIRFLOW_ADMIN_PASSWORD": 24,
    "REDIS_PASSWORD": 24,
    "GRAFANA_ADMIN_PASSWORD": 24,
    "PGADMIN_PASSWORD": 24,
}

if not ENV_EXAMPLE.exists():
    raise SystemExit(".env.example not found")

if ENV_FILE.exists():
    print(".env already exists. Skipping generation.")
    raise SystemExit(0)

# Generate secrets
values = {}
for key, length in KEYS_TO_GEN.items():
    values[key] = secrets.token_urlsafe(length)[:length]

# Superset secret key
values["SUPERSET_SECRET_KEY"] = secrets.token_hex(32)

# Airflow fernet key (32 urlsafe base64)
values["AIRFLOW__CORE__FERNET_KEY"] = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8")

# Defaults
values.setdefault("DF_HOSTNAME", DEFAULT_HOST)
values["SUPERSET_BASE_URL"] = f"http://{DEFAULT_HOST}/superset"
values["AIRFLOW__WEBSERVER__BASE_URL"] = f"http://{DEFAULT_HOST}/airflow"
values["PGADMIN_EMAIL"] = "admin@example.com"
values["AIRFLOW_UID"] = str(os.getuid())
values.setdefault("SUPERSET_DB", "superset")
values.setdefault("AIRFLOW_DB", "airflow")

# Read example and write .env
lines = []
for line in ENV_EXAMPLE.read_text().splitlines():
    if not line or line.startswith("#") or "=" not in line:
        lines.append(line)
        continue
    key, _ = line.split("=", 1)
    if key in values:
        lines.append(f"{key}={values[key]}")
    else:
        lines.append(line)

ENV_FILE.write_text("\n".join(lines) + "\n")

# Write credentials file
CREDS_FILE.parent.mkdir(parents=True, exist_ok=True)
creds = [
    "DataFoundry Credentials (auto-generated)",
    "========================================",
    f"DF_HOSTNAME={DEFAULT_HOST}",
    "",
    f"Postgres user: datafoundry",
    f"Postgres password: {values['POSTGRES_PASSWORD']}",
    "",
    f"Superset admin: admin",
    f"Superset password: {values['SUPERSET_ADMIN_PASSWORD']}",
    "",
    f"Airflow admin: airflow",
    f"Airflow password: {values['AIRFLOW_ADMIN_PASSWORD']}",
    "",
    f"Grafana admin: admin",
    f"Grafana password: {values['GRAFANA_ADMIN_PASSWORD']}",
    "",
    f"pgAdmin email: {values['PGADMIN_EMAIL']}",
    f"pgAdmin password: {values['PGADMIN_PASSWORD']}",
]
CREDS_FILE.write_text("\n".join(creds) + "\n")

print("Generated .env and data/credentials.txt")
