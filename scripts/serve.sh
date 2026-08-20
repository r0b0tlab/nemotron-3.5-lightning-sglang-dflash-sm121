#!/usr/bin/env bash
# DFlash serve profile: NVIDIA Nemotron-3.5-Lightning-30B-A3B-NVFP4 on SGLang / SM121.
# One GB10 (DGX Spark). Production window 50,016; capacity window 1,000,000.
#
# Usage:
#   IMAGE=<pinned-sglang-image> MODEL_DIR=... DRAFT_DIR=... bash serve.sh production|capacity
#
# The container runs detached; readiness is FAIL-CLOSED: probe /health until it
# reports ready, then /v1/models must show max_model_len == 50016 (production).
set -euo pipefail

PROFILE="${1:-production}"
IMAGE="${IMAGE:?set IMAGE to the pinned sglang image (digest preferred)}"
MODEL_DIR="${MODEL_DIR:-$HOME/models/nemotron-lightning/Weights}"
DRAFT_DIR="${DRAFT_DIR:-$HOME/models/nemotron-lightning/Weights-DFlash}"
NAME="nemotron-lightning-dflash-${PROFILE}"
PORT="${PORT:-30000}"

if [ "$PROFILE" = "production" ]; then
  CTX="--context-length 50016"
elif [ "$PROFILE" = "capacity" ]; then
  CTX="--context-length 1000000"
  MRR="1"
  CAP_ENV="-e SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN=1"
elif [ "$PROFILE" = "ar-baseline" ]; then
  CTX="--context-length 50016"
  NAME="nemotron-lightning-ar"
else
  echo "unknown profile: $PROFILE (want production|capacity|ar-baseline)" >&2
  exit 2
fi

JIT_CACHE="${JIT_CACHE:-$HOME/.cache/sglang-jit}"
MRR="${MRR:-6}"
CAP_ENV="${CAP_ENV:-}"

if [ "$PROFILE" = "ar-baseline" ]; then
  SPEC_ARGS=""
else
  SPEC_ARGS="--speculative-algorithm DFLASH --speculative-draft-model-path /models/draft --speculative-dflash-block-size 4"
fi

docker rm -f "$NAME" >/dev/null 2>&1 || true
mkdir -p "$JIT_CACHE/tvm-ffi" "$JIT_CACHE/sglang"

docker run --name "$NAME" --detach \
  --gpus all --ipc=host --network=host --cap-add SYS_NICE \
  $CAP_ENV \
  --cpus 14 --ulimit memlock=-1:-1 --cap-add=IPC_LOCK \
  -v "$MODEL_DIR:/models/target:ro" \
  -v "$DRAFT_DIR:/models/draft:ro" \
  -v "$JIT_CACHE/tvm-ffi:/root/.cache/tvm-ffi" \
  -v "$JIT_CACHE/sglang:/root/.cache/sglang" \
  "$IMAGE" \
  python3 -m sglang.launch_server \
    --model-path /models/target \
    --served-model-name nvidia/nemotron-3.5-lightning-30b-a3b \
    $CTX \
    --mamba-backend flashinfer \
    --mamba-ssm-dtype float16 \
    --mem-fraction-static 0.70 \
    --max-running-requests "$MRR" \
    --cuda-graph-max-bs-decode 8 \
    --kv-cache-dtype fp8_e4m3 \
    --attention-backend flashinfer \
    --disable-flashinfer-autotune \
    --moe-runner-backend marlin \
    --reasoning-parser nemotron_3 \
    --tool-call-parser qwen3_coder \
    --enable-metrics \
    $SPEC_ARGS \
    --host 0.0.0.0 \
    --port "$PORT"

echo "started $NAME; wait for readiness with scripts/wait_ready.sh"
