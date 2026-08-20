#!/usr/bin/env python3
"""1M-context NIAH 75% capacity probe for the DFlash capacity serve.

Depth = 0.75 * (1_000_000 - 256) = 749,808 tokens, needle R0B0-NIAH-7K3M.
Uses the server's own tokenizer via /tokenize to build the exact context.
Usage: python3 niah_capacity_probe.py <out_dir>
"""
import json
import os
import sys
import time
import urllib.request

PORT = os.environ.get("PORT", "30000")
BASE = f"http://127.0.0.1:{PORT}"
MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"
OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)

DEPTH = int(0.75 * (1_000_000 - 256))
NEEDLE_CODE = "R0B0-NIAH-7K3M"
NEEDLE = f"The special passcode is {NEEDLE_CODE}. Remember it."

FILLER = (
    "The history of the small coastal village was written by the sea itself. "
    "Every tide brought new driftwood, and every storm redrew the shoreline. "
    "The lighthouse keeper recorded it all in a leather-bound journal. "
)


def token_count(text):
    req = urllib.request.Request(
        f"{BASE}/tokenize",
        data=json.dumps({"prompt": text}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.load(r)
    return d.get("count") or len(d.get("tokens") or [])


def post(path, payload, timeout=7200):
    req = urllib.request.Request(
        f"{BASE}/v1{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


t0 = time.time()
filler_tok = token_count(FILLER)
reps = DEPTH // filler_tok + 1
context = (FILLER * reps)[: DEPTH * 4]  # chars approx 4/token
while token_count(context) < DEPTH:
    context += FILLER * 100
ctx_tok = token_count(context)
print(f"context built: {ctx_tok} tokens (target {DEPTH}) in {time.time()-t0:.0f}s")

prompt = context + "\n\n" + NEEDLE + "\n\nWhat is the special passcode? Reply with only the code."
t1 = time.time()
resp = post("/chat/completions", {
    "model": MODEL,
    "messages": [{"role": "user", "content": prompt}],
    "temperature": 0, "max_tokens": 64,
    "chat_template_kwargs": {"enable_thinking": False},
}, timeout=7200)
wall = time.time() - t1
answer = resp["choices"][0]["message"]["content"]
usage = resp.get("usage") or {}
result = {
    "depth_tokens": ctx_tok,
    "target_depth": DEPTH,
    "needle": NEEDLE_CODE,
    "answer": answer,
    "passed": NEEDLE_CODE in answer,
    "wall_s": round(wall, 1),
    "prompt_tokens": usage.get("prompt_tokens"),
    "completion_tokens": usage.get("completion_tokens"),
    "finish_reason": resp["choices"][0].get("finish_reason"),
    "invalid_for_publish": True,
}
json.dump(result, open(os.path.join(OUT, "depth-749808.json"), "w"), indent=2)
print("RESULT:", json.dumps({k: result[k] for k in
      ("passed", "answer", "wall_s", "prompt_tokens", "completion_tokens")}, indent=1))
sys.exit(0 if result["passed"] else 1)
