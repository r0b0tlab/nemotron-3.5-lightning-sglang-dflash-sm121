#!/usr/bin/env python3
"""Throughput-everywhere aggregation for r0b0bench outputs.

Walk an output root, find every lane data JSON (top-level dict with 'rows'
and 'summary'), and compute client-side e2e throughput per lane:
  - e2e_tok_s_total = sum(completion_tokens) / sum(elapsed_s)   (wall-accurate)
  - e2e_tok_s_mean / median over per-request completion_tokens/elapsed_s
Plus per-lane error rows and infra counts.

Usage: python3 lane_throughput.py <output_root> <out_json> <out_md>
"""
import json
import os
import statistics
import sys


def find_lane_data(root):
    lanes = {}
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in sorted(filenames):
            if not fn.endswith(".json") or fn in ("lane_result.json", "report.json", "protocol.json"):
                continue
            path = os.path.join(dirpath, fn)
            try:
                blob = json.load(open(path))
            except Exception:
                continue
            if isinstance(blob, dict) and isinstance(blob.get("rows"), list) and isinstance(blob.get("summary"), dict):
                lane_id = blob.get("summary", {}).get("method") or fn[:-5]
                # prefer sibling lane_result.json lane_id
                lr = os.path.join(dirpath, "lane_result.json")
                if os.path.exists(lr):
                    try:
                        lane_id = json.load(open(lr)).get("lane_id", lane_id)
                    except Exception:
                        pass
                lanes[os.path.relpath(path, root)] = (lane_id, blob["rows"])
    return lanes


def main():
    root, out_json, out_md = sys.argv[1], sys.argv[2], sys.argv[3]
    found = find_lane_data(root)
    out = {}
    for path, (lane_id, rows) in sorted(found.items()):
        toks, secs, errs, per_row, est = [], [], 0, [], False
        for r in rows:
            u = r.get("usage") or {}
            t = u.get("completion_tokens")
            if not t and r.get("response"):
                t = len(r["response"]) // 4  # documented char/4 estimate
                est = True
            s = r.get("elapsed_s") or 0
            toks.append(t or 0)
            secs.append(s)
            if r.get("error"):
                errs += 1
            if t and s > 0:
                per_row.append(t / s)
        lat = [s for s in secs if s > 0]
        out[lane_id] = {
            "source": path,
            "n_rows": len(rows),
            "completion_tokens_total": int(sum(toks)),
            "estimated_tokens": est,
            "wall_s_total": round(sum(secs), 2),
            "mean_latency_s": round(statistics.mean(lat), 2) if lat else None,
            "median_latency_s": round(statistics.median(lat), 2) if lat else None,
            "e2e_tok_s_total": round(sum(toks) / sum(secs), 2) if sum(toks) and sum(secs) > 0 else None,
            "e2e_tok_s_mean": round(statistics.mean(per_row), 2) if per_row else None,
            "e2e_tok_s_median": round(statistics.median(per_row), 2) if per_row else None,
            "error_rows": errs,
        }
    json.dump(out, open(out_json, "w"), indent=2, sort_keys=True)
    lines = [
        "| lane | n | wall s | mean lat s | med lat s | out tok | e2e tok/s (usage-backed) | err rows |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for lane_id, v in sorted(out.items()):
        lines.append(
            f"| {lane_id} | {v['n_rows']} | {v['wall_s_total']} | {v['mean_latency_s']} | {v['median_latency_s']} "
            f"| {v['completion_tokens_total']}{'*' if v['estimated_tokens'] else ''} "
            f"| {v['e2e_tok_s_total'] if (v['e2e_tok_s_total'] is not None and not v['estimated_tokens']) else 'n/a'} | {v['error_rows']} |"
        )
    open(out_md, "w").write("\n".join(lines) + "\n")
    print(f"wrote {out_json} ({len(out)} lanes) and {out_md}")


if __name__ == "__main__":
    main()
