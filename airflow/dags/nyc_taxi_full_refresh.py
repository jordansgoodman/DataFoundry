from __future__ import annotations

import os
from datetime import datetime

import subprocess
from airflow import DAG
from airflow.operators.python import PythonOperator

DEFAULT_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2023-01.parquet"

def full_refresh() -> None:
    os.environ["NYC_TAXI_URL"] = os.environ.get("NYC_TAXI_URL", DEFAULT_URL)
    subprocess.run(
        ["python", "/opt/airflow/dags/nyc_taxi_dlt.py"],
        check=True,
    )


with DAG(
    dag_id="nyc_taxi_full_refresh",
    start_date=datetime(2024, 1, 1),
    schedule_interval="@once",
    catchup=False,
    tags=["datafoundry"],
) as dag:
    PythonOperator(task_id="full_refresh", python_callable=full_refresh)
