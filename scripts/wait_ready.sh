#!/usr/bin/env bash
# Fail-closed readiness gate. Do NOT declare READY on container Up.
set -euo pipefail
NAME="${1:-nemotron-lightning-dflash-production}"
PORT="${2:-30000}"
MAX_ATTEMPTS="${3:-60}"
INTERVAL=10

for i in $(seq 1 "$MAX_ATTEMPTS"); do
  if curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
    echo "READY after $((i*INTERVAL))s"
    curl -fsS "http://127.0.0.1:${PORT}/v1/models" | python3 -m json.tool
    exit 0
  fi
  sleep "$INTERVAL"
done
echo "NOT READY after $((MAX_ATTEMPTS*INTERVAL))s" >&2
docker logs --tail 80 "$NAME" 2>&1 | tail -40 >&2
exit 1
