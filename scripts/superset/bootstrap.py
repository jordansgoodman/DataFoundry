import os

from superset import db
from superset.connectors.sqla.models import SqlaTable
from superset.models.core import Database

pg_user = os.environ.get("POSTGRES_USER")
pg_password = os.environ.get("POSTGRES_PASSWORD")
pg_db = os.environ.get("POSTGRES_DB")

uri = f"postgresql+psycopg2://{pg_user}:{pg_password}@postgres:5432/{pg_db}"

name = "DataFoundry Postgres"

database = db.session.query(Database).filter_by(database_name=name).one_or_none()
if not database:
    database = Database(
        database_name=name,
        sqlalchemy_uri=uri,
        expose_in_sqllab=True,
        allow_run_async=True,
    )
    db.session.add(database)
    db.session.commit()

schema = "analytics"
this_table = "nyc_taxi_yellow_tripdata"

dataset = (
    db.session.query(SqlaTable)
    .filter_by(database_id=database.id, schema=schema, table_name=this_table)
    .one_or_none()
)

if not dataset:
    dataset = SqlaTable(
        table_name=this_table,
        schema=schema,
        database=database,
    )
    db.session.add(dataset)
    db.session.commit()
