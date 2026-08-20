import importlib
import importlib.metadata
import json
import pathlib
import sys

MODEL = pathlib.Path('/model')

config = json.loads((MODEL / 'config.json').read_text())
index = json.loads((MODEL / 'model.safetensors.index.json').read_text())
weight_map = index['weight_map']
expected = [MODEL / f'model-{i:05d}-of-00052.safetensors' for i in range(1, 53)]
missing = [p.name for p in expected if not p.is_file()]
if missing:
    raise SystemExit(f'missing_shards={missing}')

mtp_keys = sum(1 for key in weight_map if key.startswith('mtp.'))
if mtp_keys == 0:
    raise SystemExit('trained_mtp_tensors=0')

import torch
import vllm
try:
    print(f'fastokens={importlib.metadata.version("fastokens")}')
except importlib.metadata.PackageNotFoundError:
    raise SystemExit('fastokens_missing')

print(json.dumps({
    'vllm': vllm.__version__,
    'torch': torch.__version__,
    'torch_cuda': torch.version.cuda,
    'device_count': torch.cuda.device_count(),
    'device_capability': torch.cuda.get_device_capability(0) if torch.cuda.is_available() else None,
    'model_architecture': config.get('architectures'),
    'model_type': config.get('model_type'),
    'model_max_position_embeddings': config.get('max_position_embeddings'),
    'shards': len(expected),
    'index_tensors': len(weight_map),
    'trained_mtp_tensors': mtp_keys,
    'index_total_size': index.get('metadata', {}).get('total_size'),
}, sort_keys=True))

for module_name in ('vllm._C_stable_libtorch', 'vllm._moe_C_stable_libtorch'):
    importlib.import_module(module_name)
    print(f'import_ok={module_name}')

fp4_check = getattr(torch.ops._C, 'cutlass_scaled_mm_supports_fp4', None)
if fp4_check is None:
    raise SystemExit('fp4_support_op_missing')
print(f'fp4_support_sm121={fp4_check(121)}')

nemotron = importlib.import_module('vllm.model_executor.models.nemotron_h')
print(f'nemotron_h_module={nemotron.__file__}')
print(f'nemotron_h_class={hasattr(nemotron, "NemotronHForCausalLM")}')

from vllm.tool_parsers import ToolParserManager
from vllm.reasoning.abs_reasoning_parsers import ReasoningParserManager
print(f'tool_parser_step3p5={ToolParserManager.get_tool_parser("step3p5")}')
print(f'reasoning_parser_nemotron_v3={ReasoningParserManager.get_reasoning_parser("nemotron_v3")}')

try:
    print(f'flashinfer_python={importlib.metadata.version("flashinfer-python")}')
except importlib.metadata.PackageNotFoundError:
    print('flashinfer_python=not-found')

site_roots = [pathlib.Path(p) for p in sys.path if p and pathlib.Path(p).is_dir()]
patterns = ('*_vllm_fa2_C*.so', '*_vllm_fa3_C*.so', '*marlin*.so')
for pattern in patterns:
    hits = sorted({str(p) for root in site_roots for p in root.rglob(pattern)})
    print(json.dumps({'fallback_pattern': pattern, 'count': len(hits), 'sample': hits[:10]}, sort_keys=True))
