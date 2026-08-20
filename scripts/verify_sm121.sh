#!/usr/bin/env bash
# SM121 native-backend audit, run on the campaign host against a live container.
# Proves: exact image identity, SM121 device capability, sglang version,
# and that the serve log resolved marlin MoE + flashinfer mamba/attention + fp8 KV.
set -euo pipefail
NAME="${1:?usage: verify_sm121.sh <container-name>}"
IMAGE_ID="$(docker inspect "$NAME" --format '{{.Image}}')"
echo "container_image_id=$IMAGE_ID"
docker inspect "$NAME" --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' \
  | sed 's/^/image_revision_label=/'

echo "--- device capability (in container) ---"
docker exec "$NAME" python3 -c \
  'import torch; print("capability:", torch.cuda.get_device_capability(0))' 2>/dev/null

echo "--- sglang version (in container) ---"
docker exec "$NAME" python3 -c \
  'import sglang, importlib.metadata as md; print("sglang:", sglang.__version__); print("dist:", md.version("sglang"))' 2>/dev/null

echo "--- backend resolution from serve log ---"
docker logs "$NAME" 2>&1 | grep -iE "marlin|flashinfer|moe|mamba|kv_cache|kv cache" | head -25

echo "--- emulation/fallback markers (must be empty) ---"
docker logs "$NAME" 2>&1 | grep -iE "fallback|emulat|not supported|downgrad" | head -10 || true
echo "audit done"
