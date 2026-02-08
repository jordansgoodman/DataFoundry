#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "python3 not found. Install Python 3.11+ and re-run."
  exit 1
fi

if [[ ! -d "${VENV_DIR}" ]]; then
  "$PYTHON_BIN" -m venv "${VENV_DIR}"
fi

chmod +x "${VENV_DIR}/bin/activate" || true
source "${VENV_DIR}/bin/activate"
python -m pip install --upgrade pip
pip install -r requirements-dev.txt

echo "Dev venv ready at ${VENV_DIR}/bin/python"
