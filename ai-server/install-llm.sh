#!/usr/bin/env bash
set -euo pipefail

# Always run from this script’s folder
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Pick a Python (assumes python3 exists; adjust if needed)
PY=python3
command -v "$PY" >/dev/null 2>&1 || { echo "❌ python3 not found"; exit 1; }

# Create venv if missing, then activate
[ -f .venv/bin/activate ] || "$PY" -m venv .venv
source .venv/bin/activate

# Install/upgrade vLLM in this venv
python -m pip install --upgrade pip
pip install --upgrade vllm

echo "✅ vLLM installed in $(which python)"
