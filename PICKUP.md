# PICKUP — Nemotron 3.5 Lightning + DFlash SGLang SM121 campaign

State as of 2026-08-20 ~06:30 CDT. Campaign is **parked on a node-availability
blocker**; everything below is verified and committed.

## What is done (verified)

- **Weights admitted**: target `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4`
  @ `e8f3c7c4` (55/55 LFS oids byte-exact; node3 `~/models/nemotron-lightning/Weights`);
  DFlash head `nvidia/...-NVFP4-DFlash` @ `7fc1f1ff` (oid-exact;
  `~/models/nemotron-lightning/Weights-DFlash`).
- **Image gate resolved with root cause**: v0.5.17 and dev@c0b6474b reject the
  MIXED_PRECISION quant config (fix `resolve_checkpoint_quant_spec` only on
  main after 08-18, unpublished in images). Selected: `dev-nemotron3-5-lightning`
  (index `a04d9a1a…`, arm64 `6da24ff7…`; same commit gd59c1ddf7 as the
  proven 08-12 pin e5e3cdb9). See `runtime/image-provenance.json`.
- **Repo**: this tree, commits `503b951` → `f6ef214`. Full standard layout
  (scripts/ docker/ runtime/ benchmark/ vendored r0b0bench 1.0.0rc2 + bfcl
  adapter + thinking-allowed.patch, tests/, docs/AGENTS.md,
  THIRD_PARTY_NOTICES.md). `.venv` on node3 has r0b0bench 1.0.0rc2 +
  bfcl-eval 2025.12.17.
- **Serve cell**: `scripts/serve.sh` / `runtime/entrypoint.sh` (DFlash b4,
  Marlin MoE, FP8 KV, flashinfer, 50016 prod / 1M capacity, mem-fraction .70,
  max-running 6). Admission canaries: `scripts/admit_canary.py`;
  throughput-everywhere: `scripts/lane_throughput.py`, `scripts/spec_snapshot.sh`.

## The blocker (do not re-litigate without new evidence)

Six controlled boots on node3 (matrix in `docs/ADMISSION-BLOCKER.md`):
AR and DFlash, graphs on/off, both digests, static ragged verify, no mamba
cache extras → Nemotron-H never completes engine startup on node3
(graph capture deadlock, or eager first-request deadlock) with NVRM memdesc
OOM bursts. Same code served on HEAD 08-12. HEAD is currently busy with the
user's Atlas production cell (96% GPU) — do not disrupt it without explicit go.

## Resume paths (user decision)

### A. Run on HEAD (recommended once Atlas is free / user authorizes)
```bash
# 1. confirm HEAD free: nvidia-smi + docker ps (Atlas stopped by user)
# 2. weights: ~/Documents/Nemotron Lightning/Weights — hash-admit vs
#    hf-manifest.json oids (node3 evidence tree); fetch DFlash head:
hf download nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4-DFlash \
  --revision 7fc1f1ff4b82b917efbd0710df0872c2bb89caa5 \
  --local-dir ~/models/nemotron-lightning/Weights-DFlash
# 3. pull image: lmsysorg/sglang:dev-nemotron3-5-lightning (digests in provenance)
# 4. rsync this repo from node3 (or git bundle) + .venv rebuild
# 5. bash scripts/serve.sh production; scripts/wait_ready.sh; admit_canary.py
# 6. Phases 4-7 per the plan .hermes/plans/2026-08-19_224839-*.md
```

### B. Fix node3 (driver rollback — user's call, Puzzle-75B precedent)
Roll back node3 to driver 580.95.05 + kernel 6.11.0-1016, reboot, re-run the
boot-matrix rows D and E (AR graphs/on + AR eager) before DFlash.

### C. New image publishes
When an lmsysorg/sglang image contains `resolve_checkpoint_quant_spec`
(+ #35265/#34561), re-run the Phase-2 gate: device-free probes → live admission
on a free node → then the full pipeline.

## Invariants

- Frozen DFlash profile: `--speculative-dflash-block-size 4`; never stack with
  MTP; Marlin MoE is the official required path (not a fallback).
- 11-lane thinking-on suite at `max_model_len 50016`; 1M NIAH 749,808 as a
  separate `invalid_for_publish=true` capacity row.
- Publish = GH repo (private→public on user go) + GHCR click-run image with
  registry digest + anonymous pull + cold click-run from public tree +
  r0b0bench ledger. No HF card (08-11 decision). Never bundle weights.
