#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
AUDIT_VENV="${SECURITY_AUDIT_VENV:-.security-audit-venv}"
PIP_TIMEOUT="${PIP_TIMEOUT:-30}"
PIP_AUDIT_SERVICE="${PIP_AUDIT_SERVICE:-osv}"
PIP_AUDIT_TIMEOUT="${PIP_AUDIT_TIMEOUT:-30}"
PIP_AUDIT_REQUIREMENTS="${PIP_AUDIT_REQUIREMENTS:-requirements.txt}"

"${PYTHON_BIN}" -m venv "${AUDIT_VENV}"
# shellcheck source=/dev/null
source "${AUDIT_VENV}/bin/activate"

python -m pip --timeout "${PIP_TIMEOUT}" install --upgrade pip pip-audit
pip-audit \
  --vulnerability-service "${PIP_AUDIT_SERVICE}" \
  --timeout "${PIP_AUDIT_TIMEOUT}" \
  --requirement "${PIP_AUDIT_REQUIREMENTS}" \
  --no-deps \
  --disable-pip \
  --progress-spinner off

if command -v osv-scanner >/dev/null 2>&1; then
  osv-scanner scan source -r . || osv-scanner -r .
else
  echo "osv-scanner is not installed; skipping OSV lockfile scan."
  echo "Install it from https://google.github.io/osv-scanner/ to include this check locally."
fi
