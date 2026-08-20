#!/usr/bin/env python3
"""Sanitize staged evidence: scrub host-private identifiers before commit.

Usage: sanitize_evidence.py <results_evidence_dir>
Replaces: /home/r0b0tdgx -> /home/<user>, node hostnames -> <node3>,
private LAN IPs -> <lan-ip>.
"""
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
USER = "r0b0tdgx"
HOSTS = {"gn100-2eea": "<node3>", "r0b0t-dgx": "<head>", "r0b0tdgx1": "<node2>"}
IP_RE = re.compile(r"192\.168\.\d{1,3}\.\d{1,3}")

changed = 0
for p in sorted(root.rglob("*")):
    if not p.is_file():
        continue
    if p.suffix not in (".json", ".md", ".txt", ".log", ".csv", ".yaml"):
        continue
    text = p.read_text(errors="replace")
    orig = text
    text = text.replace(f"/home/{USER}", "/home/<user>")
    for h, sub in HOSTS.items():
        text = text.replace(h, sub)
    text = IP_RE.sub("<lan-ip>", text)
    if text != orig:
        p.write_text(text)
        changed += 1
print(f"sanitized {changed} files under {root}")
