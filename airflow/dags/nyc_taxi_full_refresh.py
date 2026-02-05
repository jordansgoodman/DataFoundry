from __future__ import annotations

import os
from datetime import datetime

import requests
import subprocess
from airflow import DAG
from airflow.operators.python import PythonOperator

DEFAULT_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2023-01.parquet"
SUPERSET_URL = os.environ.get("SUPERSET_URL", "http://superset-web:8088")

def full_refresh() -> None:
    os.environ["NYC_TAXI_URL"] = os.environ.get("NYC_TAXI_URL", DEFAULT_URL)
    subprocess.run(
        ["python", "/opt/airflow/dags/nyc_taxi_dlt.py"],
        check=True,
    )


def _superset_login(session: requests.Session) -> str:
    username = os.environ["SUPERSET_ADMIN_USERNAME"]
    password = os.environ["SUPERSET_ADMIN_PASSWORD"]
    payload = {
        "provider": "db",
        "refresh": True,
        "username": username,
        "password": password,
    }
    resp = session.post(f"{SUPERSET_URL}/api/v1/security/login", json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()["access_token"]


def register_in_superset() -> None:
    pg_user = os.environ["POSTGRES_USER"]
    pg_password = os.environ["POSTGRES_PASSWORD"]
    pg_db = os.environ["POSTGRES_DB"]

    database_name = "DataFoundry Postgres"
    schema = "analytics"
    table_name = "nyc_taxi_yellow_tripdata"
    sqlalchemy_uri = f"postgresql+psycopg2://{pg_user}:{pg_password}@postgres:5432/{pg_db}"

    session = requests.Session()
    token = _superset_login(session)
    headers = {"Authorization": f"Bearer {token}"}

    # Upsert database
    resp = session.get(
        f"{SUPERSET_URL}/api/v1/database/",
        headers=headers,
        params={"q": f'{{"filters":[{{"col":"database_name","opr":"eq","value":"{database_name}"}}]}}'},
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()
    ids = [item["id"] for item in result.get("result", [])]
    if ids:
        database_id = ids[0]
    else:
        create_payload = {
            "database_name": database_name,
            "sqlalchemy_uri": sqlalchemy_uri,
            "expose_in_sqllab": True,
            "allow_run_async": True,
        }
        create = session.post(
            f"{SUPERSET_URL}/api/v1/database/",
            headers=headers,
            json=create_payload,
            timeout=30,
        )
        create.raise_for_status()
        database_id = create.json()["id"]

    # Upsert dataset
    resp = session.get(
        f"{SUPERSET_URL}/api/v1/dataset/",
        headers=headers,
        params={
            "q": (
                "{"
                f"\"filters\":["
                f"{{\"col\":\"table_name\",\"opr\":\"eq\",\"value\":\"{table_name}\"}},"
                f"{{\"col\":\"schema\",\"opr\":\"eq\",\"value\":\"{schema}\"}},"
                f"{{\"col\":\"database\",\"opr\":\"rel_o_m\",\"value\":{database_id}}}"
                "]}"
            )
        },
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()
    if not result.get("result"):
        create_payload = {
            "database": database_id,
            "schema": schema,
            "table_name": table_name,
        }
        create = session.post(
            f"{SUPERSET_URL}/api/v1/dataset/",
            headers=headers,
            json=create_payload,
            timeout=30,
        )
        create.raise_for_status()


with DAG(
    dag_id="nyc_taxi_full_refresh",
    start_date=datetime(2024, 1, 1),
    schedule_interval="@once",
    catchup=False,
    tags=["datafoundry"],
) as dag:
    load_task = PythonOperator(task_id="full_refresh", python_callable=full_refresh)
    register_task = PythonOperator(task_id="register_in_superset", python_callable=register_in_superset)
    load_task >> register_task
