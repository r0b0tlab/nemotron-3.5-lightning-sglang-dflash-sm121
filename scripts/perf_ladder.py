#!/usr/bin/env python3
"""Prefill proxy + concurrency ladder for the DFlash serve.

Usage: python3 perf_ladder.py <out_dir> [mode]
  mode=prefill : N reps of a ~14k-token prompt, 128 out, thinking-off
  mode=ladder  : concurrency levels [1,2,4,6], 3 reps each, 2048 out, thinking-off
"""
import concurrent.futures
import json
import os
import statistics
import sys
import threading
import time
import urllib.request

PORT = os.environ.get("PORT", "30000")
BASE = f"http://127.0.0.1:{PORT}/v1"
MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"
OUT = sys.argv[1]
MODE = sys.argv[2] if len(sys.argv) > 2 else "ladder"
os.makedirs(OUT, exist_ok=True)

LONG_PROMPT = ("The history of operating systems is long and rich. " * 700)  # ~14k chars


def post(payload, timeout=7200):
    req = urllib.request.Request(
        f"{BASE}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.load(r)
    wall = time.time() - t0
    usage = resp.get("usage") or {}
    out_tok = usage.get("completion_tokens") or 0
    ptok = usage.get("prompt_tokens") or 0
    return {"wall_s": wall, "out_tok": out_tok, "ptok": ptok, "ok": True}


def payload(prompt, out_tokens):
    return {"model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0, "max_tokens": out_tokens,
            "chat_template_kwargs": {"enable_thinking": False}}


def prefill():
    rows = []
    for i in range(1, 4):
        r = post(payload(LONG_PROMPT, 128))
        r["rep"] = i
        r["prompt_tok_s"] = round(r["ptok"] / r["wall_s"], 1) if r["wall_s"] else 0
        rows.append(r)
        print(f"prefill rep {i}: prompt {r['ptok']} tok in {r['wall_s']:.1f}s "
              f"= {r['prompt_tok_s']} prompt tok/s, {r['out_tok']} out")
    json.dump({"mode": "prefill_proxy_14k", "rows": rows}, open(os.path.join(OUT, "prefill.json"), "w"), indent=2)


def level(c, reps):
    rows = []
    for rep in range(1, reps + 1):
        t0 = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=c) as ex:
            futs = [ex.submit(post, payload(
                "Explain quantum computing and its applications in cryptography, "
                "materials science, and optimization, in detail.", 2048)) for _ in range(c)]
            res = [f.result(timeout=7200) for f in futs]
        wall = time.time() - t0
        agg = sum(r["out_tok"] for r in res) / wall if wall else 0
        rows.append({"level": c, "rep": rep, "wall_s": round(wall, 1),
                     "agg_tok_s": round(agg, 2), "n_ok": sum(r["ok"] for r in res)})
        print(f"c{c} rep {rep}: {rows[-1]['agg_tok_s']} tok/s aggregate "
              f"({rows[-1]['n_ok']}/{c} ok)")
    return rows


def ladder():
    all_rows = []
    for c in [1, 2, 4, 6]:
        all_rows += level(c, 3)
    per = {}
    for c in [1, 2, 4, 6]:
        vals = [r["agg_tok_s"] for r in all_rows if r["level"] == c]
        per[str(c)] = {"median": round(statistics.median(vals), 2), "rows": vals}
    json.dump({"mode": "concurrency_ladder_2048", "levels": per, "rows": all_rows},
              open(os.path.join(OUT, "ladder.json"), "w"), indent=2)
    print("LADDER MEDIANS:", {k: v["median"] for k, v in per.items()})


if MODE == "prefill":
    prefill()
else:
    ladder()
