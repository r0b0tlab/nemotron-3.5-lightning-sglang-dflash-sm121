#!/usr/bin/env bash
# Snapshot SGLang speculative-decoding counters from the /metrics endpoint.
# Version-proof: captures every metric line mentioning "spec" so deltas can be
# computed per benchmark window regardless of exact counter names.
# Usage: spec_snapshot.sh <label> <output_dir>
set -euo pipefail
LABEL="${1:?usage: spec_snapshot.sh <label> <output_dir>}"
OUT="${2:?output dir required}"
PORT="${PORT:-30000}"
mkdir -p "$OUT"
curl -fsS "http://127.0.0.1:${PORT}/metrics" 2>/dev/null \
  | grep -i "spec" \
  > "${OUT}/spec-${LABEL}-$(date +%Y%m%dT%H%M%S).txt" || { echo "metrics fetch failed"; exit 1; }
echo "spec snapshot ${LABEL} -> $(ls -t ${OUT}/spec-${LABEL}-*.txt | head -1)"
