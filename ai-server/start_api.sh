#!/usr/bin/env bash
set -euo pipefail
THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load portable env (picks /workspace or $HOME)
source "$THIS_DIR/env.auto.sh"

# First-time dependency install? Run run.sh once before using this script.
if [ ! -f "$THIS_DIR/.venv/bin/activate" ]; then
  echo "❌ venv missing. Run ./run.sh once to install deps."
  exit 1
fi

# Activate venv
source "$THIS_DIR/.venv/bin/activate"

# (Optional) quick GPU/CPU pick for Whisper like run.sh
if ldconfig -p 2>/dev/null | grep -q "libcudnn_ops_infer.so.8"; then
  export WHISPER_DEVICE="${WHISPER_DEVICE:-cuda}"
  export WHISPER_COMPUTE="${WHISPER_COMPUTE:-float16}"
else
  export WHISPER_DEVICE="${WHISPER_DEVICE:-cpu}"
  export WHISPER_COMPUTE="${WHISPER_COMPUTE:-float32}"
fi

# Start API
exec python -m uvicorn server:app --host 0.0.0.0 --port "${PORT:-8000}"
