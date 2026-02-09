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
    "BI_ADMIN_PASSWORD": 24,
    "AIRFLOW_ADMIN_PASSWORD": 24,
    "GRAFANA_ADMIN_PASSWORD": 24,
    "PGADMIN_PASSWORD": 24,
}

DEFAULTS = {
    "DF_HOSTNAME": DEFAULT_HOST,
    "POSTGRES_USER": "datafoundry",
    "POSTGRES_PASSWORD": "datafoundry",
    "POSTGRES_DB": "datafoundry",
    "AIRFLOW_DB": "airflow",
    "BI_ADMIN_USERNAME": "admin",
    "BI_ADMIN_PASSWORD": "admin123",
    "AIRFLOW_ADMIN_USERNAME": "airflow",
    "AIRFLOW_ADMIN_PASSWORD": "airflow123",
    "AIRFLOW_ADMIN_EMAIL": "airflow@datafoundry.local",
    "GRAFANA_ADMIN_PASSWORD": "admin123",
    "PGADMIN_EMAIL": "admin@example.com",
    "PGADMIN_PASSWORD": "pgadmin123",
    "AIRFLOW__WEBSERVER__WEB_SERVER_HOST": "0.0.0.0",
    "AIRFLOW__WEBSERVER__WEB_SERVER_PORT": "8080",
    "AIRFLOW__WEBSERVER__WEB_SERVER_URL_PREFIX": "/airflow",
}


def load_env_file(path: Path) -> dict:
    values = {}
    if not path.exists():
        return values
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        values[key] = value
    return values


if not ENV_EXAMPLE.exists():
    raise SystemExit(".env.example not found")

env_values = load_env_file(ENV_FILE)
generated_env = False

if not ENV_FILE.exists():
    # Generate secrets for a fresh .env
    values = {}
    for key, length in KEYS_TO_GEN.items():
        values[key] = secrets.token_urlsafe(length)[:length]
    values["AIRFLOW__CORE__FERNET_KEY"] = base64.urlsafe_b64encode(
        secrets.token_bytes(32)
    ).decode("utf-8")
    generated_env = True
else:
    values = {}

# Merge defaults + existing env + generated values
effective = dict(DEFAULTS)
effective.update(env_values)
effective.update(values)

host = effective.get("DF_HOSTNAME", DEFAULT_HOST)
effective.setdefault("BI_BASE_URL", f"http://{host}:8080/bi")
effective.setdefault("AIRFLOW__WEBSERVER__BASE_URL", f"http://{host}:8080/airflow")
effective.setdefault("GRAFANA_ROOT_URL", f"http://{host}:8080/grafana/")
effective.setdefault("AIRFLOW_UID", str(os.getuid()))

if generated_env:
    lines = []
    for line in ENV_EXAMPLE.read_text().splitlines():
        if not line or line.startswith("#") or "=" not in line:
            lines.append(line)
            continue
        key, _ = line.split("=", 1)
        if key in effective:
            lines.append(f"{key}={effective[key]}")
        else:
            lines.append(line)
    ENV_FILE.write_text("\n".join(lines) + "\n")

# Write credentials file (always)
CREDS_FILE.parent.mkdir(parents=True, exist_ok=True)
creds = [
    "DataFoundry Credentials (auto-generated)",
    "========================================",
    f"DF_HOSTNAME={host}",
    "",
    f"Postgres user: {effective.get('POSTGRES_USER', 'datafoundry')}",
    f"Postgres password: {effective.get('POSTGRES_PASSWORD', 'datafoundry')}",
    f"Postgres database: {effective.get('POSTGRES_DB', 'datafoundry')}",
    "",
    f"BI admin: {effective.get('BI_ADMIN_USERNAME', 'admin')}",
    f"BI password: {effective.get('BI_ADMIN_PASSWORD', 'admin123')}",
    "",
    f"Airflow admin: {effective.get('AIRFLOW_ADMIN_USERNAME', 'airflow')}",
    f"Airflow password: {effective.get('AIRFLOW_ADMIN_PASSWORD', 'airflow123')}",
    "",
    f"Grafana admin: admin",
    f"Grafana password: {effective.get('GRAFANA_ADMIN_PASSWORD', 'admin123')}",
    "",
    f"pgAdmin email: {effective.get('PGADMIN_EMAIL', 'admin@example.com')}",
    f"pgAdmin password: {effective.get('PGADMIN_PASSWORD', 'pgadmin123')}",
]
CREDS_FILE.write_text("\n".join(creds) + "\n")

if generated_env:
    print("Generated .env and data/credentials.txt")
else:
    print("Wrote data/credentials.txt from existing .env/defaults")
