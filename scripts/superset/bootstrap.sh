#!/usr/bin/env bash
set -euo pipefail

superset shell <<'PY'
from superset import app

with app.app_context():
    exec(open('/app/scripts/bootstrap.py').read())
PY
