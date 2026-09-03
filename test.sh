#!/usr/bin/env bash

# Read-only smoke test for the interview demo.
# It deliberately avoids /api/chat/send unless RUN_LLM=1 is set.
set -Eeuo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:5173}"
CURL_TIMEOUT="${CURL_TIMEOUT:-10}"

pass_count=0
fail_count=0

check() {
  local name="$1"
  local url="$2"
  local status

  if status="$(curl --silent --show-error --fail --max-time "$CURL_TIMEOUT" \
      -o /dev/null -w '%{http_code}' "$url")" && [[ "$status" == "200" ]]; then
    printf 'PASS  %-24s %s\n' "$name" "$url"
    pass_count=$((pass_count + 1))
  else
    printf 'FAIL  %-24s %s\n' "$name" "$url" >&2
    fail_count=$((fail_count + 1))
  fi
}

printf 'Oncall Opinion Analyse demo smoke test\n'
printf 'API: %s\n' "$BASE_URL"
printf 'UI : %s\n\n' "$FRONTEND_URL"

check 'API root' "$BASE_URL/"
check 'liveness' "$BASE_URL/health"
check 'agent readiness' "$BASE_URL/ready"
check 'chat modes' "$BASE_URL/api/chat/modes"
check 'visualization examples' "$BASE_URL/api/chat/visualize/examples"
check 'skill catalog' "$BASE_URL/api/skills/"
check 'frontend' "$FRONTEND_URL/"

if [[ "${RUN_LLM:-0}" == "1" ]]; then
  printf '\nLLM smoke test enabled; this may incur provider cost.\n'
  response="$(curl --silent --show-error --fail --max-time 60 \
    -H 'Content-Type: application/json' \
    -d '{"message":"请用一句话说明 Ping 的 P95 指标含义","mode":"sequential"}' \
    "$BASE_URL/api/chat/send")"
  if [[ -n "$response" ]]; then
    printf 'PASS  %-24s chat response received\n' 'LLM chat'
    pass_count=$((pass_count + 1))
  else
    printf 'FAIL  %-24s empty response\n' 'LLM chat' >&2
    fail_count=$((fail_count + 1))
  fi
fi

printf '\nSummary: %d passed, %d failed\n' "$pass_count" "$fail_count"
(( fail_count == 0 ))
