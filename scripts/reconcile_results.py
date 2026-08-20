#!/usr/bin/env python3
"""Reconcile one corrected lane into a prior report with explicit provenance."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--full-report', type=Path, required=True)
    ap.add_argument('--replacement-report', type=Path, required=True)
    ap.add_argument('--lane', required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()

    full = json.loads(args.full_report.read_text())
    replacement = json.loads(args.replacement_report.read_text())
    replacement_lanes = [x for x in replacement.get('lanes', []) if x.get('lane_id') == args.lane]
    if len(replacement_lanes) != 1:
        raise SystemExit(f'replacement must contain exactly one {args.lane} lane')
    lane = replacement_lanes[0]
    if lane.get('status') != 'PASS' or lane.get('infra_errors', 0) != 0:
        raise SystemExit('replacement lane is not PASS with zero infrastructure errors')

    merged = copy.deepcopy(full)
    found = False
    for i, old in enumerate(merged.get('lanes', [])):
        if old.get('lane_id') == args.lane:
            merged['lanes'][i] = lane
            found = True
    if not found:
        raise SystemExit(f'full report has no {args.lane} lane')

    merged['infra_errors_total'] = sum(int(x.get('infra_errors', 0)) for x in merged['lanes'])
    merged['invalid_for_publish'] = True
    merged['reconciliation'] = {
        'status': 'PASS_WITH_DISCLOSURE',
        'retained_full_run': str(args.full_report),
        'replacement_lane_report': str(args.replacement_report),
        'replacement_lane': args.lane,
        'successful_lanes_not_rerun': [
            x.get('lane_id') for x in merged['lanes'] if x.get('lane_id') != args.lane
        ],
        'publication_note': 'Secondary reconciled evidence; not a single-process full-suite run.',
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + '\n')
    print(args.output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
