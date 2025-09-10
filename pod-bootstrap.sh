#!/usr/bin/env bash
set -euo pipefail

# --- locate ai-server directory no matter where this script lives ---
SDIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "$SDIR/ai-server" ]; then
  AI_DIR="$SDIR/ai-server"
elif [ -f "$SDIR/server.py" ] && [ -d "$SDIR/../ai-server" ]; then
  # script was dropped inside ui-dashboard/ or similar — fallback
  AI_DIR="$(cd "$SDIR/../ai-server" && pwd)"
elif [ -f "$SDIR/server.py" ]; then
  # script is itself in ai-server
  AI_DIR="$SDIR"
elif [ -d "$SDIR/../ai-server" ]; then
  AI_DIR="$(cd "$SDIR/../ai-server" && pwd)"
else
  echo "❌ Could not locate ai-server directory from: $SDIR" >&2
  exit 1
fi
REPO_DIR="$(cd "$AI_DIR/.." && pwd)"

echo "📁 REPO_DIR=$REPO_DIR"
echo "📦 AI_DIR=$AI_DIR"

# --- basic tools (idempotent) ---
apt-get update -y
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  python3-venv python3-pip sox curl jq git wget

# --- ensure scripts executable (ignore missing) ---
chmod +x "$AI_DIR"/{install-piper.sh,install-llm.sh,env.auto.sh,start_vllm.sh,start_api.sh,run.sh,make_voice_assets.sh} 2>/dev/null || true

echo "➡️  Installing Piper + voices…"
bash "$AI_DIR/install-piper.sh"

echo "➡️  Installing LLM (vLLM deps/model)…"
bash "$AI_DIR/install-llm.sh"

echo "➡️  Building TTS assets (greeting + fillers)…"
bash "$AI_DIR/make_voice_assets.sh"

echo "➡️  Starting vLLM on :8011…"
bash "$AI_DIR/start_vllm.sh" &

# Wait for vLLM
echo -n "   Waiting for vLLM"
for i in {1..90}; do
  if curl -fsS http://127.0.0.1:8011/v1/models >/dev/null 2>&1; then
    echo " ✓"
    break
  fi
  echo -n "."
  sleep 1
done

echo "➡️  Starting FastAPI on :8000…"
if [ ! -d "$AI_DIR/.venv" ]; then
  bash "$AI_DIR/run.sh" &
else
  bash "$AI_DIR/start_api.sh" &
fi

# Wait for API
echo -n "   Waiting for API"
for i in {1..60}; do
  if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then
    echo " ✓"
    break
  fi
  echo -n "."
  sleep 1
done

echo "✅ Pod is up."
echo "   UI:        http://<pod-ip>:8000/ui/"
echo "   Assets:    http://<pod-ip>:8000/assets/"
echo "   Health:    http://<pod-ip>:8000/health"
