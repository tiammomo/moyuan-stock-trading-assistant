#!/usr/bin/env bash

trim_env_text() {
  local text="$1"
  text="${text#"${text%%[![:space:]]*}"}"
  text="${text%"${text##*[![:space:]]}"}"
  printf '%s' "$text"
}

strip_env_quotes() {
  local value="$1"
  if [ "${#value}" -ge 2 ]; then
    local first_char="${value:0:1}"
    local last_char="${value: -1}"
    if [ "$first_char" = "$last_char" ] && { [ "$first_char" = "\"" ] || [ "$first_char" = "'" ]; }; then
      value="${value:1:${#value}-2}"
    fi
  fi
  printf '%s' "$value"
}

load_root_env() {
  local root_dir="$1"
  local env_file="${2:-$root_dir/.env}"
  local raw_line=""
  local line=""
  local key=""
  local value=""

  if [ ! -f "$env_file" ]; then
    return 0
  fi

  while IFS= read -r raw_line || [ -n "$raw_line" ]; do
    line="$(trim_env_text "$raw_line")"

    case "$line" in
      "" | \#* | \[*)
        continue
        ;;
      export\ *)
        line="$(trim_env_text "${line#export }")"
        ;;
    esac

    case "$line" in
      *=*) ;;
      *)
        continue
        ;;
    esac

    key="$(trim_env_text "${line%%=*}")"
    if [ -z "$key" ]; then
      continue
    fi

    value="$(trim_env_text "${line#*=}")"
    value="$(strip_env_quotes "$value")"

    if [ -z "${!key+x}" ]; then
      export "$key=$value"
    fi
  done < "$env_file"
}
