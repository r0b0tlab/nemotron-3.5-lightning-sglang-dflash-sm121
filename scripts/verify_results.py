#!/usr/bin/env python3
"""Fail-closed verification for a reconciled r0b0bench report."""
from __future__ import annotations

import json
import sys
from pathlib import Path

EXPECTED = ['canary','bfcl_mt','bfcl_ast','latency','concurrency','throughput','niah','qa','ifeval','humaneval','gsm8k']


def main() -> int:
    if len(sys.argv) != 2:
        print(f'usage: {sys.argv[0]} REPORT.json', file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    data = json.loads(path.read_text())
    lanes = {x.get('lane_id'): x for x in data.get('lanes', [])}
    missing = [x for x in EXPECTED if x not in lanes]
    bad = [x for x in EXPECTED if x in lanes and (lanes[x].get('status') != 'PASS' or lanes[x].get('infra_errors', 0) != 0)]
    if missing or bad or data.get('infra_errors_total', 0) != 0:
        print(json.dumps({'status':'FAIL','missing':missing,'bad':bad,'infra_errors_total':data.get('infra_errors_total')}))
        return 1
    gsm = lanes['gsm8k'].get('summary') or {}
    # This package's measured value (DFlash b4 thinking-on, 2026-08-20 run);
    # the vendored vLLM verifier pinned 189/200 for that package's MTP run.
    if gsm.get('n') != 200 or gsm.get('correct') != 192:
        print(json.dumps({'status':'FAIL','gsm8k_summary':gsm}))
        return 1
    print(json.dumps({'status':'PASS','lanes':EXPECTED,'infra_errors_total':0,'gsm8k':'192/200'}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
