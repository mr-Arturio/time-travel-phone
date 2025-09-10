#!/usr/bin/env bash
set -euo pipefail

ASSETS_DIR="$(cd "$(dirname "$0")" && pwd)/assets"
mkdir -p "$ASSETS_DIR"

PIPER_BIN=${PIPER_BIN:-/root/piper/build/piper}

# Default Einstein voice (German male)
EINSTEIN_VOICE=${EINSTEIN_VOICE:-/root/piper/voices/de_DE-thorsten-high.onnx}
EINSTEIN_JSON=${EINSTEIN_JSON:-${EINSTEIN_VOICE}.json}

gen_with_voice() {
  local voice="$1"; shift
  local json="$1";  shift
  local out="$1";   shift
  local text="$*"
  if [[ ! -s "$ASSETS_DIR/$out" ]]; then
    echo "$text" | "$PIPER_BIN" --model "$voice" ${json:+-c "$json"} --output_file "$ASSETS_DIR/$out"
  fi
}

# Greeting (Einstein)
gen_with_voice "$EINSTEIN_VOICE" "$EINSTEIN_JSON" greet_einstein.wav "Hello—Einstein listening. How may I help you today?"

# Short “thinking” fillers (Einstein)
gen_with_voice "$EINSTEIN_VOICE" "$EINSTEIN_JSON" filler_1.wav "Hmm… give me a second."
gen_with_voice "$EINSTEIN_VOICE" "$EINSTEIN_JSON" filler_2.wav "Interesting—let me think."
gen_with_voice "$EINSTEIN_VOICE" "$EINSTEIN_JSON" filler_3.wav "One moment, please."
gen_with_voice "$EINSTEIN_VOICE" "$EINSTEIN_JSON" filler_4.wav "Let me check my notes."
gen_with_voice "$EINSTEIN_VOICE" "$EINSTEIN_JSON" filler_5.wav "I'll be right back."

echo "Assets ready in $ASSETS_DIR"
