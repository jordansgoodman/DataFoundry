from __future__ import annotations

import os
from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

from nyc_taxi_dlt import run as dlt_run

DEFAULT_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2023-01.parquet"


def full_refresh() -> None:
    os.environ.setdefault("HOME", "/opt/airflow")
    os.environ.setdefault("DLT_HOME", "/opt/airflow/.dlt")
    os.environ.setdefault("DLT_PROJECT_DIR", "/opt/airflow")
    os.environ["NYC_TAXI_URL"] = os.environ.get("NYC_TAXI_URL", DEFAULT_URL)
    dlt_run()


with DAG(
    dag_id="nyc_taxi_full_refresh",
    start_date=datetime(2024, 1, 1),
    schedule_interval="@once",
    catchup=False,
    tags=["datafoundry"],
) as dag:
    PythonOperator(task_id="full_refresh", python_callable=full_refresh)
