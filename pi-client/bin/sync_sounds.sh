#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./sync_sounds.sh <server_base_url>
# Example:
#   ./sync_sounds.sh http://192.168.0.155:8000
#
# If <server_base_url> is omitted, we try to derive it from $CONVERSE_URL.

# --- resolve BASE URL ---
BASE="${1:-}"
if [[ -z "${BASE}" ]]; then
  if [[ -n "${CONVERSE_URL:-}" ]]; then
    # derive base from /converse
    BASE="${CONVERSE_URL%/converse}"
  else
    echo "Usage: $0 <server_base_url>  (e.g. $0 http://192.168.0.155:8000)"
    echo "or set CONVERSE_URL, e.g. export CONVERSE_URL=http://IP:8000/converse"
    exit 1
  fi
fi

DEST="${SOUNDS_DIR:-$HOME/timephone/sounds}"
mkdir -p "$DEST"

# Helper to fetch a single server-hosted asset if missing
fetch() {
  local name="$1"
  local url="$BASE/assets/$name"
  if [[ -s "$DEST/$name" ]]; then
    echo "exists $name"
  else
    if curl -fsS "$url" -o "$DEST/$name"; then
      echo "fetched $name"
    else
      echo "missing $name (not on server)"
      rm -f "$DEST/$name" || true
    fi
  fi
}

echo "→ Syncing server-generated TTS assets from: $BASE"
fetch greet_einstein.wav
fetch filler_1.wav
fetch filler_2.wav
fetch filler_3.wav
fetch filler_4.wav || true
fetch filler_5.wav || true

# Also ensure the three local SFX are present.
# (We copy them from the repo if user uses $HOME/timephone/sounds as SOUNDS_DIR.)
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SRC_SFX="$REPO_DIR/sounds"
for sfx in dial_tone.wav ringback.wav receiver_lift.wav; do
  if [[ -r "$SRC_SFX/$sfx" && ! -s "$DEST/$sfx" ]]; then
    cp -n "$SRC_SFX/$sfx" "$DEST/$sfx" && echo "copied $sfx"
  fi
done

echo "Done. Files live in: $DEST"
