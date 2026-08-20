#!/usr/bin/env bash
# Stop the campaign serve and verify GPU release.
set -euo pipefail
NAME="${1:-nemotron-lightning-dflash-production}"
docker stop "$NAME" >/dev/null 2>&1 || true
docker rm -f "$NAME" >/dev/null 2>&1 || true
echo "container removed: $NAME"
sleep 5
PROCS="$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null | wc -l)"
echo "gpu compute processes after stop: $PROCS"
