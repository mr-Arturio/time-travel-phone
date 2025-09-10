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
  git clone --depth 1 https://github.com/rhasspy/piper.git
fi
cd /root/piper

echo "🔨 Building Piper..."
make                                # produces /root/piper/build/piper
ln -sf build/piper ./piper          # convenience launcher

# Ensure eSpeak-NG data is discoverable in common path
if [ ! -e /usr/share/espeak-ng-data ] && [ -d /usr/lib/x86_64-linux-gnu/espeak-ng-data ]; then
  ln -s /usr/lib/x86_64-linux-gnu/espeak-ng-data /usr/share/espeak-ng-data || true
fi

echo "📂 Preparing voices directory..."
mkdir -p /root/piper/voices
cd /root/piper/voices

download_voice () {
  local rel="$1"               # e.g. en/en_US/amy/low
  local fname="$2"             # e.g. en_US-amy-low.onnx
  local base="https://huggingface.co/rhasspy/piper-voices/resolve/main"
  local url="${base}/${rel}/${fname}?download=1"
  local jurl="${base}/${rel}/${fname}.json?download=1"

  if [ ! -f "${fname}" ]; then
    echo "  ⬇️  ${fname}"
    wget -qO "${fname}" "${url}"
  fi
  if [ ! -f "${fname}.json" ]; then
    echo "  ⬇️  ${fname}.json"
    wget -qO "${fname}.json" "${jurl}"
  fi
}

echo "🗣️ Downloading voices…"
# Default English voice (good general demo voice)
download_voice "en/en_US/amy/low" "en_US-amy-low.onnx"
# German Thorsten (nicer Einstein-esque timbre)
download_voice "de/de_DE/thorsten/high" "de_DE-thorsten-high.onnx"

echo "🔎 Verifying files…"
ls -lh \
  /root/piper/build/piper \
  /root/piper/voices/en_US-amy-low.onnx \
  /root/piper/voices/en_US-amy-low.onnx.json \
  /root/piper/voices/de_DE-thorsten-high.onnx \
  /root/piper/voices/de_DE-thorsten-high.onnx.json

echo "🎧 Quick smoke tests (write to /tmp)…"
echo "hello from piper (Amy)" | /root/piper/build/piper \
  -m /root/piper/voices/en_US-amy-low.onnx \
  -c /root/piper/voices/en_US-amy-low.onnx.json \
  -f /tmp/piper-amy-test.wav || true
echo "guten tag (Thorsten)" | /root/piper/build/piper \
  -m /root/piper/voices/de_DE-thorsten-high.onnx \
  -c /root/piper/voices/de_DE-thorsten-high.onnx.json \
  -f /tmp/piper-thorsten-test.wav || true
ls -lh /tmp/piper-*-test.wav || true

# Optionally build static voice assets for the Pi sync
if [ -f "/time-travel-phone/ai-server/make_voice_assets.sh" ]; then
  echo "📼 Building voice assets via make_voice_assets.sh…"
  # Use Amy by default for greetings/fillers (clear English). Change VOICE below if you prefer Thorsten.
  PIPER_BIN=/root/piper/build/piper \
  VOICE=/root/piper/voices/en_US-amy-low.onnx \
  bash /time-travel-phone/ai-server/make_voice_assets.sh
fi

echo "✅ Piper install complete."
echo "   Binary: /root/piper/build/piper (also /root/piper/piper)"
echo "   Voices: /root/piper/voices/{en_US-amy-low,on_US-amy-low.json,de_DE-thorsten-high,de_DE-thorsten-high.json}"
