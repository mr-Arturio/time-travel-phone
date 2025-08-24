#!/bin/bash
set -e

cd ~/time-travel-phone/ai-server

# Always recreate venv if missing or broken
if [ ! -f ".venv/bin/activate" ]; then
  echo "⚠️ venv missing or broken — recreating..."
  rm -rf .venv
  python3 -m venv .venv
fi

source .venv/bin/activate

# Upgrade pip + install deps
python -m pip install --upgrade pip
pip install -r requirements.txt

# --- Detect if cuDNN is installed ---
if ldconfig -p | grep -q "libcudnn_ops_infer.so.8"; then
  echo "✅ cuDNN found — using GPU (cuda)"
  export WHISPER_DEVICE=cuda
  export WHISPER_COMPUTE=float16
else
  echo "⚠️ cuDNN not found — falling back to CPU"
  export WHISPER_DEVICE=cpu
  export WHISPER_COMPUTE=float32
fi

# Whisper model
export WHISPER_MODEL=medium.en

# --- Piper (TTS) check ---
export PIPER_BIN=/root/piper/build/piper
export PIPER_VOICE=/root/piper/voices/en_US-amy-low.onnx

if [ ! -x "$PIPER_BIN" ]; then
  echo "❌ Piper binary not found at $PIPER_BIN"
  echo "👉 Please run ./install-piper.sh first"
  exit 1
fi

if [ ! -f "$PIPER_VOICE" ]; then
  echo "❌ Piper voice not found at $PIPER_VOICE"
  echo "👉 Please run ./install-piper.sh to download voices"
  exit 1
fi

# --- Run server ---
echo "🚀 Starting FastAPI server with Whisper + Piper..."
uvicorn server:app --host 0.0.0.0 --port 8000
