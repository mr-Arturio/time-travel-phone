#!/usr/bin/env bash
set -euo pipefail

# 1) Choose a base dir: persistent /workspace if found, else $HOME
if [ -d /workspace ]; then
  BASE=/workspace
else
  BASE="$HOME"
fi

# 2) Caches & temp on the chosen base
mkdir -p "$BASE/hf/huggingface" "$BASE/tmp"
chmod 1777 "$BASE/tmp" || true

export HF_HOME="$BASE/hf/huggingface"
export HUGGINGFACE_HUB_CACHE="$BASE/hf/huggingface/hub"
export TRANSFORMERS_CACHE="$BASE/hf/huggingface/hub"
export TMPDIR="$BASE/tmp"

# 3) vLLM endpoint/model defaults (override by exporting before sourcing)
export LLM_ENDPOINT="${LLM_ENDPOINT:-http://127.0.0.1:8011/v1}"
export LLM_MODEL="${LLM_MODEL:-openai/gpt-oss-20b}"

# 4) (Optional) Piper defaults — uncomment if/when you place Piper here
# export PIPER_BIN="${PIPER_BIN:-$BASE/piper/piper}"
# export PIPER_VOICE="${PIPER_VOICE:-$BASE/piper/voices/en_US-amy-low.onnx}"
# export PIPER_JSON="${PIPER_JSON:-${PIPER_VOICE}.json}"

echo "[env.auto] BASE=$BASE"
echo "[env.auto] HF_HOME=$HF_HOME"
echo "[env.auto] TMPDIR=$TMPDIR"
echo "[env.auto] LLM_ENDPOINT=$LLM_ENDPOINT"
echo "[env.auto] LLM_MODEL=$LLM_MODEL"
