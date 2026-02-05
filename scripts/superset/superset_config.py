import os

SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY", "change_me")
WEBSERVER_BASEURL = os.environ.get("SUPERSET_BASE_URL", "http://localhost/superset")
ENABLE_PROXY_FIX = True

REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = os.environ.get("REDIS_PORT", "6379")
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "")

CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "superset_",
    "CACHE_REDIS_HOST": REDIS_HOST,
    "CACHE_REDIS_PORT": REDIS_PORT,
    "CACHE_REDIS_PASSWORD": REDIS_PASSWORD,
}

RESULTS_BACKEND = CACHE_CONFIG
