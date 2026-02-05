import json
import os

from superset import app
from superset import db
from superset.connectors.sqla.models import SqlaTable
from superset.models.dashboard import Dashboard
from superset.models.slice import Slice
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

sm = app.appbuilder.sm

def _ensure_role_copy(name: str, source: str):
    role = sm.find_role(name)
    if not role:
        role = sm.add_role(name)
    source_role = sm.find_role(source)
    if source_role:
        role.permissions = source_role.permissions
        db.session.commit()
    return role

analyst = _ensure_role_copy("Analyst", "Alpha")
viewer = _ensure_role_copy("Viewer", "Gamma")

perm = dataset.perm
sm.add_permission_view_menu("datasource access", perm)
sm.add_permission_view_menu_role(analyst, "datasource access", perm)
sm.add_permission_view_menu_role(viewer, "datasource access", perm)

def _upsert_chart(slice_name: str, viz_type: str, params: dict):
    chart = db.session.query(Slice).filter_by(slice_name=slice_name).one_or_none()
    if not chart:
        chart = Slice(
            slice_name=slice_name,
            datasource_type="table",
            datasource_id=dataset.id,
            viz_type=viz_type,
            params=json.dumps(params),
        )
        db.session.add(chart)
        db.session.commit()
    return chart

chart_total = _upsert_chart(
    "Total Trips",
    "big_number_total",
    {
        "time_range": "No filter",
        "granularity_sqla": "tpep_pickup_datetime",
        "metric": {"expressionType": "SIMPLE", "aggregate": "COUNT", "label": "count"},
        "adhoc_filters": [],
    },
)

chart_timeseries = _upsert_chart(
    "Trips By Day",
    "line",
    {
        "time_range": "No filter",
        "granularity_sqla": "tpep_pickup_datetime",
        "time_grain_sqla": "P1D",
        "metrics": [{"expressionType": "SIMPLE", "aggregate": "COUNT", "label": "count"}],
        "adhoc_filters": [],
        "row_limit": 10000,
    },
)

dashboard = db.session.query(Dashboard).filter_by(dashboard_title="NYC Taxi Overview").one_or_none()
if not dashboard:
    position = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"type": "ROOT", "children": ["GRID_ID"]},
        "GRID_ID": {"type": "GRID", "children": ["ROW-1", "ROW-2"]},
        "ROW-1": {"type": "ROW", "children": ["CHART-1"]},
        "ROW-2": {"type": "ROW", "children": ["CHART-2"]},
        "CHART-1": {
            "type": "CHART",
            "children": [],
            "meta": {"chartId": chart_total.id, "width": 6, "height": 20},
        },
        "CHART-2": {
            "type": "CHART",
            "children": [],
            "meta": {"chartId": chart_timeseries.id, "width": 12, "height": 40},
        },
    }
    dashboard = Dashboard(
        dashboard_title="NYC Taxi Overview",
        slug="nyc-taxi-overview",
        position_json=json.dumps(position),
        json_metadata=json.dumps({"timed_refresh_immune_slices": []}),
    )
    dashboard.slices.append(chart_total)
    dashboard.slices.append(chart_timeseries)
    db.session.add(dashboard)
    db.session.commit()
