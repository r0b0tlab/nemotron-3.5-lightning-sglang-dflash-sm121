#!/usr/bin/env python3
"""C1 decode benchmark: single stream, thinking-off, N reps of 2048 max tokens.

Measures e2e wall tok/s (out_tokens / wall_s) and records per-rep spec
counter windows (accept length / accept rate) from /metrics.

Usage: python3 c1_decode_bench.py <out_dir> [reps] [max_tokens]
"""
import json
import os
import re
import statistics
import sys
import time
import urllib.request

PORT = os.environ.get("PORT", "30000")
BASE = f"http://127.0.0.1:{PORT}/v1"
MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"
OUT = sys.argv[1]
REPS = int(sys.argv[2]) if len(sys.argv) > 2 else 5
MAX_TOKENS = int(sys.argv[3]) if len(sys.argv) > 3 else 2048

PROMPT = (
    "Write a detailed technical essay about the history of computer "
    "graphics, covering rasterization, ray tracing, and neural rendering, "
    "including notable algorithms, hardware milestones, and open research "
    "problems. Continue for as long as possible."
)


def metrics():
    txt = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/metrics", timeout=30).read().decode()
    out = {}
    for key in ("sglang:spec_accept_length", "sglang:spec_accept_rate"):
        m = re.search(rf"{key}{{[^}}]*}}\s+([\d.]+)", txt)
        if m:
            out[key.split(":")[1]] = float(m.group(1))
    return out


def run_rep(i):
    req = urllib.request.Request(
        f"{BASE}/chat/completions",
        data=json.dumps({
            "model": MODEL,
            "messages": [{"role": "user", "content": PROMPT}],
            "temperature": 0, "max_tokens": MAX_TOKENS,
            "chat_template_kwargs": {"enable_thinking": False},
            "ignore_eos": True,
        }).encode(),
        headers={"Content-Type": "application/json"},
    )
    m0 = metrics()
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=3600) as r:
        resp = json.load(r)
    wall = time.time() - t0
    m1 = metrics()
    usage = resp.get("usage") or {}
    out_tok = usage.get("completion_tokens")
    if not out_tok:
        out_tok = len(resp["choices"][0]["message"]["content"]) // 4
    tok_s = out_tok / wall if wall > 0 else 0.0
    row = {
        "rep": i, "wall_s": round(wall, 2), "out_tokens": out_tok,
        "tok_s": round(tok_s, 2),
        "finish_reason": resp["choices"][0].get("finish_reason"),
        "spec_before": m0, "spec_after": m1,
    }
    print(f"rep {i}: {row['tok_s']} tok/s ({out_tok} tok in {wall:.1f}s) "
          f"accept_len {m0.get('accept_length')}->{m1.get('accept_length')} "
          f"accept_rate {m0.get('accept_rate')}->{m1.get('accept_rate')}")
    return row


import os
os.makedirs(OUT, exist_ok=True)
rows = [run_rep(i) for i in range(1, REPS + 1)]
vals = [r["tok_s"] for r in rows]
summary = {
    "mode": "c1_ignore_eos",
    "max_tokens": MAX_TOKENS,
    "reps": REPS,
    "tok_s_median": round(statistics.median(vals), 2),
    "tok_s_mean": round(statistics.mean(vals), 2),
    "tok_s_min": round(min(vals), 2),
    "tok_s_max": round(max(vals), 2),
    "rows": rows,
}
json.dump(summary, open(os.path.join(OUT, "c1_decode.json"), "w"), indent=2)
print("MEDIAN:", summary["tok_s_median"], "tok/s")
