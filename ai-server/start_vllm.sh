#!/usr/bin/env bash
set -euo pipefail
THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load portable env (auto-picks /workspace or $HOME)
source "$THIS_DIR/env.auto.sh"

# Activate venv if present
source "$THIS_DIR/.venv/bin/activate" || true

# Clean old vLLM
pkill -f "vllm.entrypoints.openai.api_server" 2>/dev/null || true

# Start vLLM on 8011 using our caches/temp
nohup python -m vllm.entrypoints.openai.api_server \
  --model "$LLM_MODEL" \
  --host 127.0.0.1 --port 8011 \
  --gpu-memory-utilization 0.90 \
  --max-model-len 8192 \
  --download-dir "$HUGGINGFACE_HUB_CACHE" \
  > "$THIS_DIR/vllm.log" 2>&1 &

echo "✅ vLLM started: http://127.0.0.1:8011/v1"
