#!/usr/bin/env bash
# Remove common Python and build caches from the repository
set -eu
echo "Cleaning repository caches and build artifacts..."
find . -type d -name '__pycache__' -print0 | xargs -0 rm -rf || true
find . -type f -name '*.pyc' -print0 | xargs -0 rm -f || true
rm -rf .pytest_cache || true
rm -rf frontend/.next || true
rm -rf frontend/node_modules || true
rm -rf backend/__pycache__ || true
echo "Done."
