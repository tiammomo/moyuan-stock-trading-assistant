#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=./load-env.sh
source "$ROOT_DIR/scripts/load-env.sh"
load_root_env "$ROOT_DIR"

BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
PYTHON_VERSION="${PYTHON_VERSION:-3.12}"

port_in_use() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"$port" -sTCP:LISTEN -t >/dev/null 2>&1
    return
  fi
  if command -v ss >/dev/null 2>&1; then
    ss -ltn "( sport = :$port )" 2>/dev/null | tail -n +2 | grep -q .
    return
  fi
  return 1
}

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required to start the backend. Install uv first."
  exit 1
fi

if port_in_use "$BACKEND_PORT"; then
  echo "Backend port $BACKEND_PORT is already in use."
  exit 1
fi

cd "$ROOT_DIR/backend"

uv sync --python "$PYTHON_VERSION"
exec uv run uvicorn app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT"
