#!/usr/bin/env bash
# Clean-install check: build the wheel, install it into a fresh virtual
# environment, and run every README command.
#
# Offline adaptation: this host has no network, so the fresh venv reuses
# system site-packages (the sole runtime dependency, PyYAML) and the project
# wheel is installed with --no-deps. Dependency resolution itself is covered
# by the online CI build job.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "== building =="
uv build --offline

VENV="$(mktemp -d)/venv"
echo "== fresh venv: ${VENV} =="
uv venv "$VENV" --system-site-packages --python 3.12
uv pip install --python "$VENV/bin/python" --offline --no-deps dist/*.whl

echo "== README commands =="
"$VENV/bin/resultseal" version
"$VENV/bin/resultseal" replay fixtures/empty-result.yaml
"$VENV/bin/resultseal" replay fixtures/explicit-not-found.yaml

echo "clean-install check: PASS"
