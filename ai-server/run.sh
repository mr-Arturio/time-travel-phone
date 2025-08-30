#!/bin/bash
export LLM_ENDPOINT="http://127.0.0.1:8001/v1"
export LLM_MODEL="gpt-oss-20B" 

set -euo pipefail

# Always run from this script’s folder
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# (Re)create venv if missing/broken
if [ ! -f ".venv/bin/activate" ]; then
  echo "⚠️ venv missing or broken — recreating..."
  rm -rf .venv
  python3 -m venv .venv
fi
source .venv/bin/activate

# Deps
python -m pip install --upgrade pip
pip install -r requirements.txt

# Detect cuDNN → choose CPU/GPU for Whisper
if ldconfig -p | grep -q "libcudnn_ops_infer.so.8"; then
  echo "✅ cuDNN found — using GPU (cuda)"
  export WHISPER_DEVICE=cuda
  export WHISPER_COMPUTE=float16
else
  echo "⚠️ cuDNN not found — falling back to CPU"
  export WHISPER_DEVICE=cpu
  export WHISPER_COMPUTE=float32
fi
export WHISPER_MODEL=medium.en

# Piper (TTS)
# Try both possible build locations
if [ -x /root/piper/piper ]; then
  export PIPER_BIN=/root/piper/piper
else
  export PIPER_BIN=/root/piper/build/piper
fi
export PIPER_VOICE=/root/piper/voices/en_US-amy-low.onnx
export PIPER_JSON="${PIPER_VOICE}.json"

# eSpeak NG data path for Piper (and create a compat symlink if needed)
if [ -d /usr/lib/x86_64-linux-gnu/espeak-ng-data ]; then
  export ESPEAKNG_DATA_PATH=/usr/lib/x86_64-linux-gnu/espeak-ng-data
else
  export ESPEAKNG_DATA_PATH=/usr/share/espeak-ng-data
fi
# Ensure /usr/share path exists (some tools hardcode it)
if [ ! -e /usr/share/espeak-ng-data ] && [ -d /usr/lib/x86_64-linux-gnu/espeak-ng-data ]; then
  ln -s /usr/lib/x86_64-linux-gnu/espeak-ng-data /usr/share/espeak-ng-data || true
fi

# Sanity checks
if [ ! -x "$PIPER_BIN" ]; then
  echo "❌ Piper binary not found at $PIPER_BIN"
  echo "👉 Run ./install-piper.sh first (it builds Piper and fetches a voice)"
  exit 1
fi
if [ ! -f "$PIPER_VOICE" ] || [ ! -f "$PIPER_JSON" ]; then
  echo "❌ Piper voice or JSON missing:"
  echo "   $PIPER_VOICE"
  echo "   $PIPER_JSON"
  echo "👉 Re-run ./install-piper.sh (or download from HF) to install voices"
  exit 1
fi

# Run server
echo "🚀 Starting FastAPI server with Whisper + Piper..."
uvicorn server:app --host 0.0.0.0 --port 8000
