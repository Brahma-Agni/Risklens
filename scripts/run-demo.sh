#!/usr/bin/env bash
# Start RiskLens, generate a fresh labelled batch, score it, and write metrics.
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

# A new seed produces unique transaction IDs, so existing local data is preserved.
export DATA_GENERATOR_SEED="${1:-$(date +%s)}"

make stack-up
make stack-check
make data-generate
make data-stream
make evaluate

dashboard_port="$(docker compose port frontend-dashboard 3000 | sed 's/.*://')"
backend_port="$(docker compose port backend 8080 | sed 's/.*://')"

printf '\nDemo complete.\nDashboard: http://localhost:%s\nBackend docs: http://localhost:%s/docs\nMetrics: evaluation/reports/latest.md\n' \
  "$dashboard_port" "$backend_port"
