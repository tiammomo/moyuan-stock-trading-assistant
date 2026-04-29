#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=./load-env.sh
source "$ROOT_DIR/scripts/load-env.sh"
load_root_env "$ROOT_DIR"

FRONTEND_PORT="${FRONTEND_PORT:-3000}"

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

find_next_dev_pid() {
  local dir="$1"
  local proc_dir=""
  local process_name=""
  local cwd=""

  for proc_dir in /proc/[0-9]*; do
    process_name="$(cat "$proc_dir/comm" 2>/dev/null || true)"
    case "$process_name" in
      next-server*) ;;
      *) continue ;;
    esac
    cwd="$(readlink -f "$proc_dir/cwd" 2>/dev/null || true)"
    if [ "$cwd" = "$dir" ]; then
      basename "$proc_dir"
      return 0
    fi
  done

  return 1
}

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required to start the frontend."
  exit 1
fi

cd "$ROOT_DIR/frontend"

if existing_pid="$(find_next_dev_pid "$PWD")"; then
  echo "A Next dev server is already running for $PWD (PID $existing_pid)."
  exit 1
fi

if port_in_use "$FRONTEND_PORT"; then
  echo "Frontend port $FRONTEND_PORT is already in use."
  exit 1
fi

if [ ! -d node_modules ]; then
  if [ -f package-lock.json ]; then
    npm ci
  else
    npm install
  fi
fi

exec env PORT="$FRONTEND_PORT" npm run dev
