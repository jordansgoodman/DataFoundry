from __future__ import annotations

import os
import tempfile
from datetime import datetime

import pandas as pd
import psycopg2
import requests
from airflow import DAG
from airflow.operators.python import PythonOperator

DEFAULT_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2023-01.parquet"
SUPERSET_URL = os.environ.get("SUPERSET_URL", "http://superset-web:8088")

EXPECTED_COLUMNS = [
    "vendorid",
    "tpep_pickup_datetime",
    "tpep_dropoff_datetime",
    "passenger_count",
    "trip_distance",
    "ratecodeid",
    "store_and_fwd_flag",
    "pulocationid",
    "dolocationid",
    "payment_type",
    "fare_amount",
    "extra",
    "mta_tax",
    "tip_amount",
    "tolls_amount",
    "improvement_surcharge",
    "total_amount",
    "congestion_surcharge",
    "airport_fee",
]

DDL = """
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE TABLE IF NOT EXISTS analytics.nyc_taxi_yellow_tripdata (
  vendorid integer,
  tpep_pickup_datetime timestamp,
  tpep_dropoff_datetime timestamp,
  passenger_count integer,
  trip_distance double precision,
  ratecodeid integer,
  store_and_fwd_flag text,
  pulocationid integer,
  dolocationid integer,
  payment_type integer,
  fare_amount double precision,
  extra double precision,
  mta_tax double precision,
  tip_amount double precision,
  tolls_amount double precision,
  improvement_surcharge double precision,
  total_amount double precision,
  congestion_surcharge double precision,
  airport_fee double precision
);
"""


def _download(url: str, dest_path: str) -> None:
    with requests.get(url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8 * 1024 * 1024):
                if chunk:
                    f.write(chunk)


def _load_to_postgres(parquet_path: str) -> None:
    pg_user = os.environ["POSTGRES_USER"]
    pg_password = os.environ["POSTGRES_PASSWORD"]
    pg_db = os.environ["POSTGRES_DB"]

    df = pd.read_parquet(parquet_path)
    df.columns = [c.lower() for c in df.columns]

    for col in EXPECTED_COLUMNS:
        if col not in df.columns:
            df[col] = None

    df = df[EXPECTED_COLUMNS]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
        csv_path = tmp.name
        df.to_csv(csv_path, index=False)

    conn = psycopg2.connect(
        host="postgres",
        port=5432,
        dbname=pg_db,
        user=pg_user,
        password=pg_password,
    )
    conn.autocommit = False

    try:
        with conn.cursor() as cur:
            cur.execute(DDL)
            cur.execute("TRUNCATE TABLE analytics.nyc_taxi_yellow_tripdata;")
            with open(csv_path, "r") as f:
                cur.copy_expert(
                    "COPY analytics.nyc_taxi_yellow_tripdata FROM STDIN WITH (FORMAT CSV, HEADER TRUE)",
                    f,
                )
        conn.commit()
    finally:
        conn.close()


def full_refresh() -> None:
    url = os.environ.get("NYC_TAXI_URL", DEFAULT_URL)
    os.makedirs("/opt/airflow/data", exist_ok=True)
    parquet_path = "/opt/airflow/data/nyc_taxi.parquet"
    _download(url, parquet_path)
    _load_to_postgres(parquet_path)


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
