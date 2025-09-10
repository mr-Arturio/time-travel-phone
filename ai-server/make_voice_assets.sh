#!/usr/bin/env bash
set -euo pipefail

ASSETS_DIR="$(cd "$(dirname "$0")" && pwd)/assets"
mkdir -p "$ASSETS_DIR"

PIPER_BIN=${PIPER_BIN:-/root/piper/build/piper}
VOICE=${VOICE:-/root/piper/voices/en_US-amy-low.onnx}

# idempotent build: only synthesize if missing
gen() {
  local out="$1"; shift
  local text="$*"
  if [[ ! -s "$ASSETS_DIR/$out" ]]; then
    echo "$text" | "$PIPER_BIN" --model "$VOICE" --output_file "$ASSETS_DIR/$out"
  fi
}

# Einstein greeting (more lines later for "thinking" fillers)
gen greet_einstein.wav "Hello—Einstein listening. How may I help you today?"

# Einstein “thinking” fillers (very short)
gen filler_1.wav "Hmm… give me a second."
gen filler_2.wav "Interesting—let me think."
gen filler_3.wav "One moment, please."
gen filler_4.wav "Let me check my notes."
gen filler_5.wav "I'll be right back."

echo "Assets ready in $ASSETS_DIR"
