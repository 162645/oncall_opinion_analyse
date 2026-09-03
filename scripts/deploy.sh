#!/usr/bin/env bash

# Small, predictable operator entrypoint for local and interview deployments.
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT_DIR/docker/docker-compose.yml}"
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-oncall-demo}"

compose() {
  docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" "$@"
}

usage() {
  cat <<'EOF'
Usage: ./scripts/deploy.sh <command>

Commands:
  start       Build and start the core stack
  stop        Stop the stack without deleting volumes
  restart     Restart the core stack
  status      Show container status
  logs [name] Follow logs for the stack or one service
  health      Run the read-only demo smoke test
EOF
}

command="${1:-}"
case "$command" in
  start)
    compose up -d --build
    ;;
  stop)
    compose stop
    ;;
  restart)
    compose up -d --build
    ;;
  status)
    compose ps
    ;;
  logs)
    if [[ -n "${2:-}" ]]; then
      compose logs -f --tail=100 "$2"
    else
      compose logs -f --tail=100
    fi
    ;;
  health)
    BASE_URL="${BASE_URL:-http://127.0.0.1:8000}" \
    FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:5173}" \
    bash "$ROOT_DIR/test.sh"
    ;;
  *)
    usage
    exit 2
    ;;
esac
