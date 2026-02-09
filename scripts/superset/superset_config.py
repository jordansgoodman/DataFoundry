import os

SQLALCHEMY_DATABASE_URI = os.environ.get(
    "SUPERSET_SQLALCHEMY_DATABASE_URI",
    "postgresql+psycopg2://datafoundry:datafoundry@postgres:5432/superset",
)

SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY", "change-me")

# Keep defaults safe for local dev
WTF_CSRF_ENABLED = True
ENABLE_PROXY_FIX = True
