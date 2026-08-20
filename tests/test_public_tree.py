#!/usr/bin/env python3
"""Fail-closed public-tree tests. Run from the repo root:
    python3 tests/test_public_tree.py
Verifies the click-to-run contract of the PUBLISHED tree (no placeholders,
pinned digests, vendored benchmark snapshot, evidence present).
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAIL = []


def need(cond, msg):
    if not cond:
        FAIL.append(msg)


def read(p, default=""):
    try:
        with open(os.path.join(ROOT, p)) as f:
            return f.read()
    except FileNotFoundError:
        return default


# 1. click-run entrypoint
cc = read("scripts/click_run_dflash.sh")
need("click_run_dflash.sh" in os.listdir(os.path.join(ROOT, "scripts")), "missing scripts/click_run_dflash.sh")
need("e8f3c7c4de75ad84fe1bcef95d38eca76214480b" in cc, "click_run: target rev missing")
need("7fc1f1ff4b82b917efbd0710df0872c2bb89caa5" in cc, "click_run: draft rev missing")
need("@PINNED_IMAGE@" not in cc, "click_run: unreplaced image placeholder")
need("huggingface-cli" in cc, "click_run: no huggingface-cli download path")

# 2. Dockerfile FROM pin
df = read("docker/Dockerfile")
need(os.path.exists(os.path.join(ROOT, "docker", "Dockerfile")), "missing docker/Dockerfile")
need(re.search(r"FROM\s+\S*sha256:[0-9a-f]{64}", df) is not None, "Dockerfile FROM is not digest-pinned")
need("@PINNED_IMAGE@" not in df, "Dockerfile: unreplaced image placeholder")

# 3. serve profiles
sv = read("runtime/entrypoint.sh")
for needle in ["production", "capacity", "--speculative-algorithm DFLASH",
               "--speculative-dflash-block-size 4", "--context-length 50016",
               "--moe-runner-backend marlin", "--kv-cache-dtype fp8_e4m3"]:
    need(needle in sv, f"entrypoint missing: {needle}")

# 4. benchmark snapshot identity
ss = read("benchmark/source-state.json")
try:
    st = json.loads(ss)
    need(st.get("base_commit") == "e0f0bf667d3ea8e97f2a9c4453f94201173c7082",
         "benchmark snapshot base_commit mismatch")
    need(st.get("version") == "1.0.0rc2", "benchmark snapshot version mismatch")
    need(os.path.exists(os.path.join(ROOT, "benchmark", "thinking-allowed.patch")),
         "missing thinking-allowed.patch")
except json.JSONDecodeError:
    need(False, "benchmark/source-state.json unparsable")

# 5. README needles
rm = read("README.md")
for needle in ["Click to run", "huggingface-cli", "50016", "max_model_len",
               "r0b0bench", "lane_throughput.py", "THIRD_PARTY_NOTICES.md"]:
    need(needle in rm, f"README missing: {needle}")

# 6. provenance + notices + license + boundary
for p in ["runtime/image-provenance.json", "THIRD_PARTY_NOTICES.md", "LICENSE",
          ".gitignore"]:
    need(os.path.exists(os.path.join(ROOT, p)), f"missing {p}")
need("Scope and boundary" in rm, "README missing the Scope and boundary section")
need("docs/AGENTS.md" not in os.listdir(os.path.join(ROOT, "docs")), "docs/AGENTS.md is approval-gated; boundary lives in README")

# 7. evidence present (release trees must carry sanitized results)
need(os.path.exists(os.path.join(ROOT, "results", "evidence")), "missing results/evidence")
need(bool(os.listdir(os.path.join(ROOT, "results", "evidence"))), "results/evidence empty")

if FAIL:
    print("FAIL:")
    for f in FAIL:
        print(" -", f)
    sys.exit(1)
print("public-tree tests: PASS")
