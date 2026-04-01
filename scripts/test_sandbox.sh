#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker-compose.sandbox.yml"
ENV_FILE="$ROOT_DIR/.env.test"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/test_sandbox.sh up [scenario]
  ./scripts/test_sandbox.sh reseed [scenario]
  ./scripts/test_sandbox.sh down

Scenarios:
  minimal
  realistic
  project_heavy
  messy
EOF
}

require_env_file() {
  if [[ ! -f "$ENV_FILE" ]]; then
    echo ".env.test not found. Copy .env.test.example to .env.test first." >&2
    exit 1
  fi
}

run_reset() {
  docker compose -f "$COMPOSE_FILE" run --rm app env PYTHONPATH=/app uv run python scripts/reset_test_data.py --env-file .env.test
}

run_seed() {
  local scenario="$1"
  docker compose -f "$COMPOSE_FILE" run --rm app env PYTHONPATH=/app uv run python scripts/seed_test_data.py --env-file .env.test --scenario "$scenario"
}

command="${1:-}"
scenario="${2:-realistic}"

case "$command" in
  up)
    require_env_file
    docker compose -f "$COMPOSE_FILE" up -d postgres
    docker compose -f "$COMPOSE_FILE" build app
    run_reset
    run_seed "$scenario"
    docker compose -f "$COMPOSE_FILE" up -d app
    echo "Sandbox running at http://localhost:5510"
    echo "Scenario: $scenario"
    ;;
  reseed)
    require_env_file
    docker compose -f "$COMPOSE_FILE" up -d postgres
    docker compose -f "$COMPOSE_FILE" build app
    run_reset
    run_seed "$scenario"
    echo "Sandbox reseeded with scenario: $scenario"
    ;;
  down)
    docker compose -f "$COMPOSE_FILE" down
    ;;
  *)
    usage
    exit 1
    ;;
esac
