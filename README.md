# Nemotron 3.5 Lightning + DFlash on SGLang / SM121 (single DGX Spark)

Reproducibility package for serving **NVIDIA Nemotron 3.5 Lightning 30B-A3B NVFP4**
with the official **DFlash** speculative draft head on **SGLang**, on one
NVIDIA DGX Spark (GB10 / SM121, arm64, Ubuntu, Docker).

| Surface | Identity |
|---|---|
| Served model | `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4` @ `e8f3c7c4de75ad84fe1bcef95d38eca76214480b` |
| Draft model | `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4-DFlash` @ `7fc1f1ff4b82b917efbd0710df0872c2bb89caa5` |
| Runtime | pinned `lmsysorg/sglang` image (digest in `runtime/image-provenance.json`) |
| Serve profile | `--speculative-algorithm DFLASH --speculative-dflash-block-size 4`, Marlin W4A16_NVFP4 MoE, FP8 KV, FlashInfer attention/mamba |
| Benchmark client | r0b0bench `1.0.0rc2` @ `e0f0bf6` + thinking-allowed.patch (vendored in `benchmark/`) |

## Click to run

Prerequisites: Docker with NVIDIA Container Toolkit, `huggingface-cli`
(anonymous downloads work — both checkpoints are public), ~25 GB disk, free port 30000.

```bash
git clone https://github.com/r0b0tlab/nemotron-3.5-lightning-sglang-dflash-sm121
cd nemotron-3.5-lightning-sglang-dflash-sm121
bash scripts/click_run_dflash.sh
```

Expected end state: `wait_ready.sh` reports READY, `/v1/models` shows
`max_model_len 50016`, canary prints the correct arithmetic result, and the
server keeps serving on http://127.0.0.1:30000/v1.

Manual launch: `IMAGE=<pinned image> bash runtime/launch.sh production` (see
`runtime/launch.sh`), or run the released container image directly
(`PROFILE=production`, mounts `/models/target` + `/models/draft`).

## Serve profiles

- **production** — `--context-length 50016` (the matched evaluation window).
- **capacity** — `--context-length 1000000` + `SGLANG_ALLOW_OVERWRITE_LONGER_CONTEXT_LEN=1` (only for the 1M NIAH capacity row; not a quality-claim window).

## Benchmark identity

11-lane r0b0bench `core-subset`, native thinking-on
(`R0B0BENCH_CHAT_TEMPLATE_KWARGS='{"thinking":true,"enable_thinking":true}'`):
canary, bfcl_mt (200), bfcl_ast, latency, concurrency C1/C2/C4/C6, throughput
(decode 2048 + prefill), niah 25/50/90 of the production window, qa ARC-Easy 400,
ifeval 200 (lightweight), humaneval 164, gsm8k 200 0-shot flexible extract.

Envelopes: GSM8K 49,152; QA/IFEval/HumanEval 32,768; systems/BFCL/canary 8,192.
The 1M NIAH 75% row (depth 749,808) is a separate capacity run marked
`invalid_for_publish=true`.

**Throughput-everywhere contract:** every lane (quality included) reports
client-side e2e tok/s derived from per-request completion tokens and elapsed
seconds (`scripts/lane_throughput.py`), plus spec-decode counters
(drafted/accepted) snapshotted per lane window (`scripts/spec_snapshot.sh`).

## Results

See `results/evidence/` for sanitized per-lane evidence:
`report.json` (scores), `lane_throughput.json` (per-lane e2e tok/s),
spec-counter snapshots, and the reconciliation manifest. Summary tables below
are regenerated from that evidence.

## Results (2026-08-20, DFlash block-size 4, production window 50,016)

### 11-lane core-subset — native thinking-on (reconciled, disclosure-marked)

| Lane | Result | e2e throughput |
|---|---|---|
| canary | PASS (identity, needle, structured, tool-call, zh-arithmetic) | — |
| bfcl_mt | 117/200 = **58.5%** (official multi_turn_base) | — |
| bfcl_ast | micro 114/600 = **19.0%** (multiple/parallel/parallel_multiple) | — |
| latency | PASS | 101.5–110.5 tok/s e2e c1 |
| concurrency | PASS | c1 112.3 / c2 164.1 / c4 237.9 / c6 305.4 agg tok/s (8192-out) |
| throughput | PASS | decode 67.8 median tok/s; prefill 2,113.3 prompt tok/s |
| niah | PASS 25/50/90 (10,456 / 20,912 / 37,641) | — |
| qa | 383/400 = **95.75%** ARC-Easy | mean latency 6.9 s |
| ifeval | 174/200 = **87.0%** (lightweight constraint scorer) | mean latency 59.0 s |
| humaneval | pass@1 = **93.9%** (154/164) | — |
| gsm8k | 192/200 = **96.0%** (0-shot flexible extract) | **75.6 e2e tok/s** (usage-backed) |

`infra_errors_total = 0`. The report is `PASS_WITH_DISCLOSURE` reconciliation:
the systems block ran in one process; bfcl/qa/ifeval/gsm8k were re-run after
fixing two client-side defects (missing `soundfile`; relative dataset paths)
and humaneval after installing the `human-eval` scorer. Primary evidence for
every lane is in `results/evidence/`; see `report-reconstructed.json`.

### 1M capacity row (separate, invalid_for_publish)

- Depth 749,808 tokens (0.75 × (1,000,000 − 256)): **PASS** — needle
  `R0B0-NIAH-7K3M` returned exactly (751,611-token context, 463 s wall).

### Perf matrix (thinking-off, matched geometry)

| Metric | DFlash b4 | No-spec AR |
|---|---|---|
| C1 2048 ignore_eos | 66.67 tok/s median | 69.03 tok/s median |
| Ladder c1/c2/c4/c6 (2048-out) | 74.1 / 111.3 / 161.3 / 190.5 | 68.9 / 110.0 / 168.1 / 208.2 |
| Prefill proxy cold (~7k tok) | 4,615 prompt tok/s | ~3,100–3,900 prompt tok/s |

Spec telemetry (server counters): thinking-off C1 accept length ~2.0–2.5,
accept rate ~0.33–0.49; thinking-on batch decode accept length up to 3.8,
accept rate up to 0.93 (c4). **Honest verdict: DFlash b4 is a modest win at
low concurrency (+7.6% c1 ladder) and on thinking-on batches, a wash to
slightly negative at c4+; no-spec AR remains the throughput-max profile,
consistent with NVIDIA's guidance.**

### Reproducibility notes

- First boot JIT-compiles the sm_121a FP4 Marlin kernel via TVM-FFI
  (~10–15 min of nvcc/ptxas, CPU-bound). `serve.sh` persists
  `/root/.cache/tvm-ffi` + `/root/.cache/sglang` under `~/.cache/sglang-jit`;
  warm-cache boots are ~3.5–4 min.
- FP8 KV scaling factors default to 1.0 (checkpoint ships none); quality
  gates above all pass on the native Marlin W4A16_NVFP4 path.
- Prefill CUDA graph is auto-disabled for Nemotron-H (hybrid Mamba2) — expected.

## Scope and boundary

This package covers the SGLang + DFlash cell only. It does not cover the
vLLM package (`r0b0tlab/nemotron-3.5-lightning-sm121-nvfp4`), the SGLang
MTP/EAGLE package (`r0b0tlab/nemotron-3.5-lightning-sglang-sm121`), the Atlas
engine, or any other model family — do not reuse those numbers here.
No model weights, datasets, credentials, or raw BFCL traces are stored in
this repository. See `docs/AGENTS.md` for the working boundary.

## License

MIT (this package). Model checkpoints are NVIDIA's and are NOT redistributed
here. See `THIRD_PARTY_NOTICES.md`.
