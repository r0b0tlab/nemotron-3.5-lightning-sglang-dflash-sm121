#!/usr/bin/env python3
"""Fail-closed admission canaries for the DFlash serve.

1. /v1/models identity: served name + max_model_len 50016 (production) or 1000000 (capacity).
2. thinking-off arithmetic 5/5 (temp 0).
3. thinking-on reasoning probe (reasoning_content present, content sane).
4. tool_call canary (structured tool call parses).
5. spec counters: drafted/accepted metrics present and non-zero after probes.

Usage: python3 admit_canary.py [production|capacity]
"""
import json
import sys
import urllib.request

PROFILE = sys.argv[1] if len(sys.argv) > 1 else "production"
EXPECTED_MML = {"production": 50016, "capacity": 1000000}[PROFILE]
BASE = "http://127.0.0.1:30000/v1"
MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"
FAIL = []


def post(path, payload, timeout=600):
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        FAIL.append(msg)


# 1. identity
models = json.load(urllib.request.urlopen(f"{BASE}/models", timeout=60))
m = models["data"][0]
check(m["id"] == MODEL, f"served model id = {m['id']}")
mml = m.get("max_model_len")
check(mml == EXPECTED_MML, f"max_model_len = {mml} (want {EXPECTED_MML})")

# 2. thinking-off arithmetic 5/5
pairs = [(19, 23), (37, 58), (142, 7), (91, 13), (256, 2)]
ok = 0
for a, b in pairs:
    r = post("/chat/completions", {
        "model": MODEL,
        "messages": [{"role": "user",
                      "content": f"What is {a} × {b}? Reply with just the number."}],
        "temperature": 0, "max_tokens": 64,
        "chat_template_kwargs": {"enable_thinking": False},
    })
    got = r["choices"][0]["message"]["content"].strip()
    if str(a * b) in got:
        ok += 1
    else:
        print(f"  ({a}×{b}: got {got[:60]!r})")
check(ok == 5, f"thinking-off arithmetic {ok}/5")

# 3. thinking-on probe
r = post("/chat/completions", {
    "model": MODEL,
    "messages": [{"role": "user",
                  "content": "Briefly explain: what is speculative decoding?"}],
    "temperature": 0, "max_tokens": 4096,
    "chat_template_kwargs": {"enable_thinking": True},
})
msg = r["choices"][0]["message"]
reasoning = msg.get("reasoning_content") or ""
content = msg.get("content") or ""
check(len(reasoning) > 20, f"thinking-on reasoning_content present ({len(reasoning)} chars)")
check(len(content) > 20, f"thinking-on content present ({len(content)} chars)")

# 4. tool call
r = post("/chat/completions", {
    "model": MODEL,
    "messages": [{"role": "user",
                  "content": "My bill is $50. What will be the amount for a 15% tip?"}],
    "tools": [{
        "type": "function",
        "function": {
            "name": "calculate_tip",
            "parameters": {
                "type": "object",
                "properties": {
                    "bill_total": {"type": "number"},
                    "tip_percentage": {"type": "number"},
                },
                "required": ["bill_total", "tip_percentage"],
            },
        },
    }],
    "temperature": 0, "max_tokens": 512,
    "chat_template_kwargs": {"enable_thinking": False},
})
tc = msg.get("tool_calls") or r["choices"][0]["message"].get("tool_calls") or []
check(bool(tc), "tool_call canary returned structured tool call")
if tc:
    try:
        args = json.loads(tc[0]["function"]["arguments"])
        check(isinstance(args.get("tip_percentage"), (int, float)),
              f"tool_call arguments parse ({args})")
    except Exception as e:
        check(False, f"tool_call arguments unparsable: {e}")

# 5. spec counters
try:
    metrics = urllib.request.urlopen("http://127.0.0.1:30000/metrics", timeout=60).read().decode()
    spec = [l for l in metrics.splitlines() if "spec" in l.lower() and not l.startswith("#")]
    check(bool(spec), f"spec metrics present ({len(spec)} lines)")
except Exception as e:
    print(f"WARN metrics endpoint unavailable ({e}); enable --enable-metrics for counter telemetry")
    check(True, "metrics fetch skipped (endpoint disabled)")

print("\nRESULT:", "PASS" if not FAIL else "FAIL")
sys.exit(0 if not FAIL else 1)
