#!/bin/bash
set -euo pipefail

echo "🧰 Installing Piper build/runtime deps..."
apt-get update -y
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  build-essential cmake git wget curl \
  espeak-ng espeak-ng-data libespeak-ng1

echo "📥 Cloning/Updating Piper..."
cd /root
if [ ! -d piper ]; then
  git clone https://github.com/rhasspy/piper.git
fi
cd /root/piper

echo "🔨 Building Piper..."
make                      # produces /root/piper/build/piper
ln -sf build/piper ./piper # convenience: /root/piper/piper also works

# Ensure tools that expect /usr/share/... can find eSpeak data
if [ ! -e /usr/share/espeak-ng-data ] && [ -d /usr/lib/x86_64-linux-gnu/espeak-ng-data ]; then
  ln -s /usr/lib/x86_64-linux-gnu/espeak-ng-data /usr/share/espeak-ng-data || true
fi

echo "🗣️ Downloading Amy (en_US) voice (ONNX + JSON)..."
mkdir -p /root/piper/voices
cd /root/piper/voices

VOICE="en_US-amy-low.onnx"
VOICE_JSON="${VOICE}.json"
BASE_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/low"

if [ ! -f "$VOICE" ]; then
  wget -O "$VOICE"      "${BASE_URL}/${VOICE}?download=1"
fi
if [ ! -f "$VOICE_JSON" ]; then
  wget -O "$VOICE_JSON" "${BASE_URL}/${VOICE_JSON}?download=1"
fi

echo "🔎 Verifying files..."
ls -lh "/root/piper/build/piper" "/root/piper/voices/$VOICE" "/root/piper/voices/$VOICE_JSON"

echo "🎧 Quick smoke test (creates /tmp/piper-install-test.wav)..."
echo "hello from piper" | /root/piper/build/piper \
  -m "/root/piper/voices/$VOICE" \
  -c "/root/piper/voices/$VOICE_JSON" \
  -f /tmp/piper-install-test.wav || true
ls -lh /tmp/piper-install-test.wav || true

echo "✅ Piper install complete."
echo "   Binary: /root/piper/build/piper (also /root/piper/piper)"
echo "   Voice : /root/piper/voices/$VOICE"
