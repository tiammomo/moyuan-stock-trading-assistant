#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=./load-env.sh
source "$ROOT_DIR/scripts/load-env.sh"
load_root_env "$ROOT_DIR"

BACKEND_SCRIPT="$ROOT_DIR/scripts/dev-backend.sh"
FRONTEND_SCRIPT="$ROOT_DIR/scripts/dev-frontend.sh"

backend_pid=""
frontend_pid=""

cleanup() {
  local exit_code="${1:-0}"
  trap - EXIT INT TERM

  if [ -n "$backend_pid" ] && kill -0 "$backend_pid" >/dev/null 2>&1; then
    kill "$backend_pid" >/dev/null 2>&1 || true
    wait "$backend_pid" 2>/dev/null || true
  fi

  if [ -n "$frontend_pid" ] && kill -0 "$frontend_pid" >/dev/null 2>&1; then
    kill "$frontend_pid" >/dev/null 2>&1 || true
    wait "$frontend_pid" 2>/dev/null || true
  fi

  exit "$exit_code"
}

on_signal() {
  echo
  echo "Stopping frontend and backend..."
  cleanup 0
}

trap 'on_signal' INT TERM
trap 'cleanup $?' EXIT

echo "Starting backend on ${BACKEND_HOST:-127.0.0.1}:${BACKEND_PORT:-8000}"
"$BACKEND_SCRIPT" &
backend_pid="$!"

echo "Starting frontend on 127.0.0.1:${FRONTEND_PORT:-3000}"
"$FRONTEND_SCRIPT" &
frontend_pid="$!"

wait -n "$backend_pid" "$frontend_pid"
exit_code="$?"
echo "A dev process exited. Shutting down the rest."
cleanup "$exit_code"
