#!/usr/bin/env bash
# CLICK-TO-RUN: serve NVIDIA Nemotron-3.5-Lightning-30B-A3B-NVFP4 + DFlash on SGLang / SM121.
#
# Prerequisites (one time):
#   - Docker with NVIDIA Container Toolkit (nvidia-docker runtime)
#   - huggingface-cli (`pip install -U "huggingface[hf_transfer]"`) — downloads are anonymous
#   - ~25 GB disk for the two public checkpoints; ~6-14 GB for the container image
#   - port 30000 free
#
# Expected end state:
#   "wait_ready.sh: READY" -> /v1/models shows max_model_len 50016
#   -> canary prints "19 × 23 = 437" with correct reasoning -> server keeps running.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${IMAGE:-}"
TARGET_REV="e8f3c7c4de75ad84fe1bcef95d38eca76214480b"
DRAFT_REV="7fc1f1ff4b82b917efbd0710df0872c2bb89caa5"
TARGET_DIR="${TARGET_DIR:-$HOME/models/nemotron-lightning/Weights}"
DRAFT_DIR="${DRAFT_DIR:-$HOME/models/nemotron-lightning/Weights-DFlash}"
NAME="nemotron-lightning-dflash-production"

# 0) sanity: docker + GPU runtime
command -v docker >/dev/null || { echo "docker not found"; exit 1; }
docker info >/dev/null 2>&1 || { echo "docker daemon not running"; exit 1; }

# 1) checkpoints (skip when a complete local tree exists)
if [ ! -f "$TARGET_DIR/model-00052-of-00052.safetensors" ]; then
  echo "[1/3] downloading target checkpoint (pinned revision)..."
  huggingface-cli download nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4 \
    --revision "$TARGET_REV" --local-dir "$TARGET_DIR"
fi
if [ ! -f "$DRAFT_DIR/model.safetensors" ]; then
  echo "[1/3] downloading DFlash draft checkpoint (pinned revision)..."
  huggingface-cli download nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4-DFlash \
    --revision "$DRAFT_REV" --local-dir "$DRAFT_DIR"
fi

# 2) image: pinned GHCR package; override with IMAGE=
if [ -z "$IMAGE" ]; then
  IMAGE="ghcr.io/r0b0tlab/nemotron-3.5-lightning-sglang-dflash-sm121:v0.1.0-sm121-dflash"
  echo "[2/3] pulling published image..."
  docker pull "$IMAGE"
fi

# 3) serve + ready gate + canary
echo "[3/3] starting server (production window 50016, DFlash block-size 4)..."
IMAGE="$IMAGE" MODEL_DIR="$TARGET_DIR" DRAFT_DIR="$DRAFT_DIR" \
  bash "$HERE/scripts/serve.sh" production

bash "$HERE/scripts/wait_ready.sh" "$NAME" 30000 60

echo "--- canary ---"
python3 - <<'PY'
import json, urllib.request
req = urllib.request.Request(
    "http://127.0.0.1:30000/v1/chat/completions",
    data=json.dumps({
        "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
        "messages": [{"role": "user", "content": "What is 19 × 23? Reply with just the number."}],
        "temperature": 0, "max_tokens": 64,
        "chat_template_kwargs": {"enable_thinking": False},
    }).encode(),
    headers={"Content-Type": "application/json"})
r = json.load(urllib.request.urlopen(req, timeout=300))
print("canary answer:", r["choices"][0]["message"]["content"].strip())
PY

echo "click-run OK — server live on http://127.0.0.1:30000/v1"
