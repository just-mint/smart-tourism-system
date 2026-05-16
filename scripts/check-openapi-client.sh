#!/usr/bin/env bash
set -euo pipefail

bash scripts/generate-client.sh

if ! git diff --exit-code -- frontend/openapi.json frontend/src/client; then
  echo "OpenAPI contract is stale. Run scripts/generate-client.sh and commit the generated changes."
  exit 1
fi
