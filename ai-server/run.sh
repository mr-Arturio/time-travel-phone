#!/bin/bash
set -e

cd ~/time-travel-phone/ai-server

# Recreate venv if missing
if [ ! -d ".venv" ]; then
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

# Piper (TTS)
export PIPER_BIN=/root/piper/piper
export PIPER_VOICE=/root/piper/voices/en_US-amy-low.onnx

# Run server
uvicorn server:app --host 0.0.0.0 --port 8000
