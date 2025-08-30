#!/bin/bash
set -euo pipefail
source /time-travel-phone/ai-server/.venv/bin/activate || true
pip install --upgrade vllm

# You’ll point VLLM_MODEL to the model name or local path
echo "✅ vLLM installed. Start with:"
echo '  python -m vllm.entrypoints.openai.api_server --model "$VLLM_MODEL" --host 127.0.0.1 --port 8001'
echo '  # Optionally: --tensor-parallel-size 2 (multi-GPU), --max-model-len 8192'
