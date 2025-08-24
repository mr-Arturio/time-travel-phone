#!/bin/bash
set -e

echo "🚀 Installing Piper dependencies..."
apt-get update
apt-get install -y build-essential espeak-ng cmake wget git

echo "📥 Cloning Piper..."
cd /root
if [ ! -d "piper" ]; then
  git clone https://github.com/rhasspy/piper.git
fi
cd piper

echo "🔨 Building Piper..."
make

# Ensure binary is available at /root/piper/piper
if [ -f "build/piper" ]; then
  cp build/piper ./piper
fi

echo "🗣️ Downloading voice model..."
mkdir -p voices
VOICE_PATH="voices/en_US-amy-low.onnx"
VOICE_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/low/en_US-amy-low.onnx"

if [ ! -f "$VOICE_PATH" ]; then
  echo "Downloading Amy (US English, low quality) voice..."
  wget "$VOICE_URL" -O "$VOICE_PATH"
else
  echo "Voice model already exists: $VOICE_PATH"
fi

echo "✅ Piper installed successfully!"
echo "Binary: /root/piper/piper"
echo "Voice:  /root/piper/$VOICE_PATH"
