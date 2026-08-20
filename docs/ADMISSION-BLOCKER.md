# Admission notes — CORRECTED (2026-08-20)

The original ADMISSION-BLOCKER.md diagnosis (environmental deadlock on node3)
was WRONG. The user's "finish this on node3" pushed a proper root-cause: the
day-0 image JIT-compiles the sm_121a FP4 Marlin GEMM kernel through TVM-FFI
(nvcc → ptxas) during the first CUDA-graph capture (or first eager forward).
That compile is CPU-bound and takes ~10-15 minutes on aarch64. Every earlier
"hang" was a boot killed mid-compile; the NVRM memdesc OOM bursts were nvcc
allocation transients. No environmental blocker exists.

## Fix (in serve.sh, committed)

- Persist the JIT caches across boots: mount `~/.cache/sglang-jit/tvm-ffi` and
  `~/.cache/sglang-jit/sglang` onto `/root/.cache/{tvm-ffi,sglang}`.
- First boot after the fix: READY (10:32:58), warm-cache boots ~210-250 s.
- Admission canary: 8/8 PASS (identity, 5/5 arithmetic, thinking-on
  reasoning+content, tool call, spec metrics).
- CUDA graphs captured with warm cache: target_verify 5.15 s, draft_decode
  0.85 s.

## Evidence to keep

- phase0/boots/ logs from the pre-fix boots (compile-in-progress evidence).
- runtime/runtime-contract.json — frozen serve profile + admission gates.
- The v0.5.17 / dev@c0b6474b image rejections (MIXED_PRECISION quant config)
  in runtime/image-provenance.json remain CORRECT and unchanged.
