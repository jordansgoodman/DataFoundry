import os
import time
from datetime import datetime, timedelta

import pandas as pd
from sqlalchemy import create_engine, text

DB_URL = os.environ.get("BI_DATABASE_URL")
POLL_SECONDS = int(os.environ.get("BI_SCHEDULER_POLL_SECONDS", "30"))

engine = create_engine(DB_URL, pool_pre_ping=True)
engine_cache = {}


def ensure_tables():
    with engine.begin() as conn:
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS bi_schedules (
              id SERIAL PRIMARY KEY,
              query_id INTEGER NOT NULL REFERENCES bi_saved_queries(id) ON DELETE CASCADE,
              name TEXT NOT NULL,
              interval_minutes INTEGER NOT NULL DEFAULT 60,
              enabled BOOLEAN NOT NULL DEFAULT TRUE,
              last_run TIMESTAMP,
              next_run TIMESTAMP
            );
            """
        ))
        conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS bi_query_results (
              id SERIAL PRIMARY KEY,
              query_id INTEGER NOT NULL REFERENCES bi_saved_queries(id) ON DELETE CASCADE,
              run_at TIMESTAMP NOT NULL DEFAULT NOW(),
              row_count INTEGER NOT NULL,
              data_json TEXT
            );
            """
        ))


def get_engine_for_datasource(datasource_id: int):
    if datasource_id in engine_cache:
        return engine_cache[datasource_id]
    with engine.connect() as conn:
        uri = conn.execute(
            text("SELECT sqlalchemy_uri FROM bi_datasources WHERE id=:id"),
            {"id": datasource_id},
        ).scalar()
    ds_engine = create_engine(uri, pool_pre_ping=True)
    engine_cache[datasource_id] = ds_engine
    return ds_engine


def run_query(sql: str, datasource_id: int):
    ds_engine = get_engine_for_datasource(datasource_id)
    with ds_engine.connect() as conn:
        df = pd.read_sql(text(sql), conn)
    return df


def process_schedule(row):
    schedule_id, query_id, interval_minutes = row

    with engine.connect() as conn:
        sql_row = conn.execute(
            text("SELECT sql, datasource_id FROM bi_saved_queries WHERE id=:id"),
            {"id": query_id},
        ).fetchone()

    if not sql_row:
        return

    df = run_query(sql_row[0], sql_row[1])
    data_json = df.to_json(orient="records")

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO bi_query_results (query_id, run_at, row_count, data_json)
                VALUES (:qid, :run_at, :rows, :data)
                """
            ),
            {
                "qid": query_id,
                "run_at": datetime.utcnow(),
                "rows": len(df),
                "data": data_json,
            },
        )
        conn.execute(
            text(
                """
                UPDATE bi_schedules
                SET last_run = :last_run,
                    next_run = :next_run
                WHERE id = :id
                """
            ),
            {
                "id": schedule_id,
                "last_run": datetime.utcnow(),
                "next_run": datetime.utcnow() + timedelta(minutes=interval_minutes),
            },
        )


if __name__ == "__main__":
    ensure_tables()
    while True:
        now = datetime.utcnow()
        with engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT id, query_id, interval_minutes
                    FROM bi_schedules
                    WHERE enabled = TRUE AND (next_run IS NULL OR next_run <= :now)
                    ORDER BY id
                    """
                ),
                {"now": now},
            ).fetchall()

        for row in rows:
            try:
                process_schedule(row)
            except Exception:
                pass

        time.sleep(POLL_SECONDS)
