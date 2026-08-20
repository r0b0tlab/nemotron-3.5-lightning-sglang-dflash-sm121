# Third-party notices

This reproducibility package uses the following third-party components.

## NVIDIA Nemotron 3.5 Lightning model checkpoints

- `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4`
- `nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4-DFlash`

Copyright NVIDIA Corporation. Distributed under the NVIDIA Open Model License
(see the LICENSE files in the Hugging Face repositories). The weights are NOT
included in this repository or in the container image.

The DFlash speculative-decoding method is described in:
"DFlash: Block Diffusion for Flash Speculative Decoding" (Hugging Face paper
2602.06036).

## SGLang

https://github.com/sgl-project/sglang — Apache License 2.0.
This package pins a published `lmsysorg/sglang` container image by digest and
does not redistribute SGLang source.

## FlashInfer

https://github.com/flashinfer-ai/flashinfer — Apache License 2.0.
Included in the pinned SGLang image.

## Marlin FP4 kernels

Marlin CUDA kernels (Apache License 2.0), included in the pinned SGLang image.

## r0b0bench

https://github.com/r0b0tlab/r0b0bench — MIT License.
Vendored snapshot under `benchmark/` (see `benchmark/LICENSE`).

## BFCL (gorilla)

https://github.com/ShishirPatil/gorilla — Apache License 2.0.
Used through the adapter scripts under `benchmark/scripts/bfcl`.
