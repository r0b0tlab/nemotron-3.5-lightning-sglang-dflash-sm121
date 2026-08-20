#!/usr/bin/env bash
# r0b0bench 11-lane core-subset driver for the DFlash serve (adapted from the
# vLLM Lightning package; endpoint/served-name switched to the SGLang cell).
#
# Suite B (thinking-on) is the primary claim package:
#   export R0B0BENCH_CHAT_TEMPLATE_KWARGS='{"thinking":true,"enable_thinking":true}'
#   export R0B0BENCH_CANARY_MAX_TOKENS=8192
#   bash scripts/run_benchmark.sh
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENDPOINT="${ENDPOINT:-http://127.0.0.1:30000/v1}"
MODEL="${MODEL:-nvidia/nemotron-3.5-lightning-30b-a3b}"
TOKENIZER="${TOKENIZER:-$HOME/models/nemotron-lightning/Weights}"
OUTPUT="${OUTPUT:-$HOME/artifacts/nemotron-lightning-optimization/sglang-dflash-20260819/r0b0bench-out}"
R0B0BENCH_BIN="${R0B0BENCH_BIN:-r0b0bench}"

# Safe default: never inline JSON inside ${VAR:-{...}} (bash closes the
# expansion at the first '}' and corrupts the payload).
if [ -z "${R0B0BENCH_CHAT_TEMPLATE_KWARGS:-}" ]; then
  R0B0BENCH_CHAT_TEMPLATE_KWARGS="$(python3 -c 'import json; print(json.dumps({"thinking": True, "enable_thinking": True}))')"
fi
python3 -c 'import json, os; json.loads(os.environ["R0B0BENCH_CHAT_TEMPLATE_KWARGS"])' \
  || { echo "R0B0BENCH_CHAT_TEMPLATE_KWARGS is not valid JSON" >&2; exit 1; }

export R0B0BENCH_CHAT_TEMPLATE_KWARGS
export R0B0BENCH_CANARY_MAX_TOKENS="${R0B0BENCH_CANARY_MAX_TOKENS:-8192}"
export R0B0BENCH_BFCL_PYTHON="${R0B0BENCH_BFCL_PYTHON:-$(command -v python3)}"
export R0B0BENCH_BFCL_SCRIPTS="${R0B0BENCH_BFCL_SCRIPTS:-$ROOT/benchmark/scripts/bfcl}"
export R0B0BENCH_SERVED_MODEL="${R0B0BENCH_SERVED_MODEL:-$MODEL}"
export BFCL_NUM_THREADS="${BFCL_NUM_THREADS:-1}"
export BFCL_MAX_TOKENS="${BFCL_MAX_TOKENS:-8192}"
export BFCL_HTTP_TIMEOUT="${BFCL_HTTP_TIMEOUT:-7200}"
export BFCL_MAX_RETRIES="${BFCL_MAX_RETRIES:-3}"

# Dataset paths: relative defaults do NOT resolve from an arbitrary CWD in
# r0b0bench 1.0.0rc2. Export absolute paths (or set them before invoking).
export R0B0BENCH_QA_DATA="${R0B0BENCH_QA_DATA:-$HOME/datasets/qa/arc_easy_test.jsonl}"
export R0B0BENCH_IFEVAL_DATA="${R0B0BENCH_IFEVAL_DATA:-$HOME/datasets/ifeval/input_data.jsonl}"
export R0B0BENCH_HUMANEVAL_DATA="${R0B0BENCH_HUMANEVAL_DATA:-$HOME/datasets/humaneval/HumanEval.jsonl}"
export R0B0BENCH_GSM8K_DATA="${R0B0BENCH_GSM8K_DATA:-$HOME/datasets/gsm8k/test.jsonl}"

mkdir -p "$OUTPUT"
exec "$R0B0BENCH_BIN" run \
  --profile "${PROFILE:-core-subset}" \
  --base-url "$ENDPOINT" \
  --model "$MODEL" \
  --tokenizer "$TOKENIZER" \
  --output "$OUTPUT" \
  --timeout "${TIMEOUT:-7200}"
