# r0b0bench implementation snapshot

This directory contains the exact model-neutral benchmark client source used for the NVIDIA Nemotron 3.5 Lightning evaluation.

- Package version: `1.0.0rc2`
- Base commit: `e0f0bf667d3ea8e97f2a9c4453f94201173c7082`
- Corrected source patch: `../benchmark/thinking-allowed.patch`
- Current patch SHA-256: `a243d10350cf83aa6dc7019d15198e2fae59cfad953a98506a638d973b961200`

Install from the repository root with:

```bash
python -m pip install -e './benchmark[bfcl,dev]'
```

The three supported profiles are `core`, `core-subset`, and `systems`. The `core-subset` profile contains the mandatory systems block plus QA@400, IFEval@200, HumanEval@164, and GSM8K@200.

Native-thinking runs must set the exact JSON request controls through `R0B0BENCH_CHAT_TEMPLATE_KWARGS` and must record effective response ceilings. Use `scripts/run_benchmark.sh` from the repository root rather than inventing a new invocation.

Benchmark outputs belong outside the checkout. This snapshot contains no datasets, weights, credentials, or raw BFCL result traces.
