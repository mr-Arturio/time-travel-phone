## Inspiration
Imagine you’re an 8th-grader in history class. Your teacher is talking about **Julius Caesar** or **Abraham Lincoln** and then asks: _“If you could call them right now, what would you ask?”_
They pull out a **rotary phone** - a real one. _“Pick one question. Dial the number. Listen.”_
You spin the dial, hold the handset to your ear, and hear a reply in the figure’s own voice and style. The contrast of vintage hardware and living answers turns a normal lesson into a core memory.

## What it does
Pick up an old rotary phone, dial a number, and ask a question. On the other end, a historical figure answers — in an era-inspired voice, style, and worldview. This project fuses retro hardware with open-source AI to create a playful, educational “timeline” you can literally dial.

_I've got Einstein on a speed dial... Do you?_

- Rotary dial selects a persona (e.g., 314 → Einstein; others coming soon).
- A Raspberry Pi inside the phone captures handset audio and posts it to a self-hosted AI server
- faster-whisper transcribes the question.
- A persona-aware prompt goes to `openai/gpt-oss-20b` served by vLLM (OpenAI-compatible).
- Piper TTS returns a reply in an era-inspired voice, played through the handset.

## How I built it
###Hardware
- Refurbished rotary phone as the enclosure; Raspberry Pi 4B mounted inside the shell.
- Mobile earbuds act as the handset speaker + microphone via a USB audio dongle.
- Rotary dial pulses read on GPIO with debouncing; hook switch detection wired to GPIO to auto start/stop recording.

###Software
- **FastAPI** server: `/health`, `/converse`, `/events`, and a `/ui` dashboard (SSE).
- **STT**: faster-whisper (configurable model, CPU by default).
- **LLM**: `openai/gpt-oss-20b` via **vLLM** (OpenAI API shim).
- **TTS**: Piper, per-persona voice model (plus simple pacing via `pause_ms`).
- **Pi client**: records 16 kHz mono WAV, posts to /converse, plays back returned WAV.

## Challenges I ran into

- Integrating the Raspberry Pi neatly inside a vintage phone shell while maintaining serviceability and airflow.
- Reliable hook-switch detection to auto start/stop recording and reset state between calls.
- Debouncing and digit accuracy on the rotary dial pulse train under noisy electrical conditions.
- Ensuring every reply is a valid WAV (sample rate, channels, PCM subtype) so playback never fails mid-demo.
- Latency tradeoffs between Whisper accuracy, LLM size, and TTS quality; budgeting response length and temperature.
- Cross-platform audio quirks between Linux on the Pi and the server environment.
- Most of the AI/Pi ecosystem is Python-based, while my proficiency is in JavaScript, so bridging that gap meant extra research, experimentation, and debugging outside my comfort zone.
- Fine-tuning the model prompts and voice settings to strike a balance between character accuracy, natural flow, and demo-ready response times.

## Accomplishments that I am proud of

- A complete, reliable end-to-end experience: pick up, dial, speak, and hear a historically grounded answer in seconds.
- Entirely self-hosted stack with gpt-oss-20b via vLLM, faster-whisper, and Piper TTS, no external AI APIs.
- Clean hardware integration: Pi, USB audio, dial, and hook switch all working inside the restored phone.
- Persona prompts that keep answers concise, in-character, and bounded by the figure’s lifetime knowledge.
- Operational resilience: health checks, environment toggles, and graceful fallbacks.

## What I learned
- **Practical phone archaeology**: classic rotary phones are line-powered; modernizing them safely means rethinking audio (use hidden USB mic/speaker) and controls (GPIO for dial + hook).
- **Linux audio pipelines**: strict WAV formatting (16 kHz, mono, PCM_16) is non-negotiable for reliable playback across tools/drivers.
- **Perceived vs. raw latency**: short, pre-recorded “thinking” fillers + tight token budgets, low temperature, and brief TTS keep the call feeling instant.
- **Persona design is a craft**: style cards, era boundaries, retrieval with citations, and concise tone improve both faithfulness and charm.
- **Rented GPU on RunPod.io**: learned to choose practical GPUs (use 20B + 4-bit on 24 GB cards), understand spot vs on-demand, open an SSH tunnel, spin up a FastAPI + Whisper stack, expose /health, and add CPU/GPU fallbacks via env vars. Also got the hang of pinning model versions, watching VRAM, and shutting pods down to control costs
- **Python + Pi stack**: got hands-on with gpiozero for switch and dial input, threading/timers for event timing, subprocess for sound playback, and requests for HTTP calls. Learned the importance of running lightweight code on the Pi (avoid heavy libs, keep processes async) and delegating LLM/TTS workloads to the server.
- **Debugging across stacks**: switching between Python (system control, AI stack) and JavaScript (my comfort zone) taught me how to translate concepts like async flows, error handling, and event-driven logic across languages.
- **Model & voice tuning**: experimented with temperature, max tokens, and few-shot prompts to balance accuracy with speed. On the voice side, tried different Piper voices and adjusted pitch/speed to keep replies both recognizable and natural.
- **Hardware/software symbiosis**: small wiring mistakes or timing drifts in the pulse train ripple all the way up to app stability, so I learned to debug holistically—from breadboard signals to cloud logs.

## What's next for Time Travel Phone
- Audio polish: add subtle line tones, ringback, and era-appropriate line static to heighten the illusion.
- Filler expansion: broaden the library of short persona “thinking” clips and vary them per persona.
- More personas: Marie Curie, Leonardo da Vinci, Ada Lovelace, Nikola Tesla, Charles Darwin, Confucius, and others, each with a style card and curated corpus.
- Kiosk mode: timed sessions, volume limiter, and on-device signage for museums and classrooms.
- Accessibility: captions on a small companion display and a handset volume rocker.
- Packaging: a turnkey image (Docker Compose + preloaded weights) for simple school/museum installs.
- Full conversations (multi-turn): True back-and-forth dialogue after advanced model training:
   - Multi-turn memory (short-term context window + persona-consistent recall).
   - Conversation manager to track topics, follow-ups, and clarifying questions.
   - RAG across turns so answers build on previous context with citations.
   - Natural turn-taking (VAD/barge-in) and streaming TTS for snappier, interruptible replies.

   ___
   # Ignore Old notes below

I prefer this step by step installation, it is easier to catch an error, debug adn test every step


## Fresh Pod:

```
# Pod shell
git clone https://github.com/mr-Arturio/time-travel-phone.git
cd time-travel-phone/ai-server

chmod +x install-piper.sh install-llm.sh env.auto.sh start_vllm.sh start_api.sh run.sh make_voice_assets.sh

# One-time installs
./install-piper.sh
./install-llm.sh

# Start vLLM (8011) – uses env.auto.sh internally
./start_vllm.sh

./make_voice_assets.sh

# First time only: set up venv + deps
./run.sh    # (creates venv, installs requirements, then starts API on :8000)
# ^ If you prefer keeping run.sh only for installs, Ctrl+C and then:
# ./start_api.sh   # start API with env.auto.sh sourced

```

Open tunnel in a new tab:
ssh -vv -N -g -i $env:USERPROFILE\.ssh\id_ed25519 -p <podPort> -L 0.0.0.0:8000:127.0.0.1:8000 root@<podIP>

Exposes your pod’s API :8000 on your laptop for the Pi to use.

curl http://localhost:8011/v1/models
curl http://localhost:8000/health

On laptop tab:

Check and update the podPort - $podPort in start-time-travel.ps1
powershell -ExecutionPolicy Bypass -File .\start-time-travel.ps1

On laptop (new window): py -3.8 C:\Users\mrart\time-travel-phone\tiny_client\client.py

##Daily start

```
cd /time-travel-phone/ai-server
bash env.auto.sh             # sets caches/TMP to /workspace (or $HOME)
./start_vllm.sh              # brings up vLLM on :8011
./start_api.sh               # brings up FastAPI on :8000

```

## To start the Pi


- git clone https://github.com/mr-Arturio/time-travel-phone.git

```
sudo apt update
sudo apt install -y sox libsox-fmt-all curl jq
# Quick check
sox --version
curl --version

```

- do all the audio and hook tests
  Run the client with the correct server URL
  export CONVERSE_URL="http://192.168.0.155:8000/converse"

```
/projects/time-travel-phone/pi-client $ ./phone.py
```

### From the Pi, verify reachability to your laptop

curl -s http://<LAPTOP_IP_ON_LAN>:8000/health | jq
curl -s http://192.168.0.155:8000/health | jq

export CONVERSE_URL="http://<your-laptop-LAN-IP>:8000/converse"
export CONVERSE_URL="http://192.168.0.155:8000/converse"
export EVENTS_BASE="http://192.168.0.155:8000"

chmod +x ~/projects/time-travel-phone/pi-client/bin/sync_sounds.sh
./sync_sounds.sh

Dashboard: http://localhost:8000/ui/
