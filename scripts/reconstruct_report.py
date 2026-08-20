#!/usr/bin/env python3
"""Reconstruct a report.json from per-lane lane_result.json files.

Usage: reconstruct_report.py <lane_dir_root> <output_report.json>
Provenance: marks the report as reconstructed-from-lane-artifacts.
"""
import json
import sys
from pathlib import Path

ORDER = ["canary", "bfcl_mt", "bfcl_ast", "latency", "concurrency",
         "throughput", "niah", "qa", "ifeval", "humaneval", "gsm8k"]

root = Path(sys.argv[1])
out = Path(sys.argv[2])
lanes = []
by_lane = {}
for lr in root.rglob("lane_result.json"):
    try:
        d = json.loads(lr.read_text())
    except Exception:
        continue
    by_lane[d.get("lane_id")] = d
for lane_id in ORDER:
    if lane_id in by_lane:
        d = by_lane[lane_id]
        lanes.append({
            "lane_id": lane_id,
            "status": d.get("status"),
            "infra_errors": int(d.get("infra_errors") or 0),
            "summary": d.get("summary"),
            "artifacts": d.get("artifacts"),
        })
    else:
        lanes.append({
            "lane_id": lane_id,
            "status": "NOT_RUN",
            "infra_errors": 0,
            "summary": {"note": "lane never reached in this run; replaced via reconciliation"},
        })
report = {
    "lanes": lanes,
    "infra_errors_total": sum(int(x.get("infra_errors") or 0) for x in lanes),
    "invalid_for_publish": True,
    "reconstruction": {
        "status": "RECONSTRUCTED_FROM_LANE_ARTIFACTS",
        "source_root": str(root),
        "note": "Primary run was terminated before report aggregation; per-lane results are intact.",
    },
}
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
print(out, "lanes:", len(lanes))
