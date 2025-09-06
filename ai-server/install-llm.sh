#!/bin/bash
set -euo pipefail

# activate venv if present (best-effort)
source /time-travel-phone/ai-server/.venv/bin/activate || true

# install/upgrade vLLM
pip install --upgrade vllm

# show how to start vLLM on the port used by your stack (8011)
echo "✅ vLLM installed. Start with:"
echo '  python -m vllm.entrypoints.openai.api_server --model "$VLLM_MODEL" --host 127.0.0.1 --port 8011'
echo '  # Optionally: --tensor-parallel-size 2 (multi-GPU), --max-model-len 8192'
