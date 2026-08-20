#!/usr/bin/env bash
# Container entrypoint: frozen DFlash serve profile.
# Mounts: target at /models/target, draft at /models/draft (read-only).
# Env: PROFILE=production|capacity, PORT (default 30000).
set -euo pipefail

PROFILE="${PROFILE:-production}"
PORT="${PORT:-30000}"

if [ "$PROFILE" = "production" ]; then
  CTX="--context-length 50016"
elif [ "$PROFILE" = "capacity" ]; then
  CTX="--context-length 1000000"
  export SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN=1
else
  echo "unknown profile: $PROFILE (want production|capacity)" >&2
  exit 2
fi

exec python3 -m sglang.launch_server \
  --model-path /models/target \
  --served-model-name nvidia/nemotron-3.5-lightning-30b-a3b \
  $CTX \
  --mamba-backend flashinfer \
  --mamba-ssm-dtype float16 \
  --mem-fraction-static 0.70 \
  --max-running-requests 6 \
  --cuda-graph-max-bs-decode 8 \
  --kv-cache-dtype fp8_e4m3 \
  --attention-backend flashinfer \
  --disable-flashinfer-autotune \
  --moe-runner-backend marlin \
  --reasoning-parser nemotron_3 \
  --tool-call-parser qwen3_coder \
  --enable-metrics \
  --speculative-algorithm DFLASH \
  --speculative-draft-model-path /models/draft \
  --speculative-dflash-block-size 4 \
  --host 0.0.0.0 \
  --port "$PORT"
