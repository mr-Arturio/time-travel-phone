# Time-Travel Phone

<small>Build for **OpenAI Open Model Hackathon**</small><br>

_An old rotary desk phone brought back to life with a Raspberry Pi and modern speech AI.
Lift the handset, dial a number, and famous person answers your call. You ask a question; he thinks, then replies out loud in a character._

### Requirements

- **Server**: Linux host or GPU pod (RunPod/AWS/etc). CPU works; GPU recommended for faster LLM/Whisper.
- **Raspberry Pi 4B** 4 GB or more with Raspberry Pi OS, Wi-Fi or Ethernet.
- **Rotary phone hardware** (mechanical dial, hook switch, shell), USB sound dongle, handset mic/earbuds. See full list with Hardware instructions here - [Hardware.md](./docs/Hardware.md)

### Software stack

- **Speech-to-Text:** faster-whisper (CPU by default; CUDA if present)
- **LLM:** vLLM serving openai/gpt-oss-20b via an OpenAI-compatible API
- **Text-to-Speech:** Piper (ONNX voice models)
- **API:** FastAPI (/converse, /health, /events) + personas in personas.json
- **Dashboard:** /ui static page consuming SSE (/events) to visualize the call

### Personalities (dial codes)

- Einstein — dial 314 to connect <br>
  _More historical personas will be added soon_

## Quickstart (step-by-step)

The steps below assume you have a running Pod (remote server) and a Pi on your LAN.

### 1. Bring up the Pod (server)

```bash
# On your pod or Linux server (SSH shell)
git clone https://github.com/mr-Arturio/time-travel-phone.git /time-travel-phone
cd /time-travel-phone/ai-server

chmod +x install-piper.sh install-llm.sh env.auto.sh \
        start_vllm.sh start_api.sh run.sh make_voice_assets.sh
```

### 2. One-time installs

```bash
# Build Piper + fetch voice
./install-piper.sh

# Install vLLM into (or alongside) the venv
./install-llm.sh
```

### 3. Start the LLM (vLLM on :8011)

```bash
./start_vllm.sh
# Expect: "✅ vLLM started: http://127.0.0.1:8011/v1"
curl -s http://127.0.0.1:8011/v1/models | head -c 200; echo
# Expect JSON with "openai/gpt-oss-20b"
```

### 4. First-time server deps + API on :8000

```bash
# Creates .venv, installs requirements, then starts API on :8000
./run.sh
# (If you prefer, Ctrl+C after deps finish, then start cleanly:)
# ./start_api.sh
```

### Verify the server

```bash
# vLLM:
curl http://127.0.0.1:8011/v1/models

# API health:
curl http://127.0.0.1:8000/health | jq
# UI:
# open http://<server-ip>:8000/ui/
```

### If your Pod is remote, expose the API on your laptop via SSH tunnel

- Windows PowerShell

```powershell
# Replace <podIP> and <podPort>
ssh -vv -N -g `
  -i $env:USERPROFILE\.ssh\id_ed25519 `
  -p <podPort> `
  -L 0.0.0.0:8000:127.0.0.1:8000 `
  -L 0.0.0.0:8011:127.0.0.1:8011 `
  root@<podIP>
```

- macOS / Linux

```bash
ssh -vv -N -g \
  -i ~/.ssh/id_ed25519 \
  -p <podPort> \
  -L 0.0.0.0:8000:127.0.0.1:8000 \
  -L 0.0.0.0:8011:127.0.0.1:8011 \
  root@<podIP>
```

Verify from your local machine (laptop):

```bash
curl http://localhost:8000/health | jq
```
>With this tunnel, your Pi can point to http://<your-laptop-LAN-IP>:8000 (or straight to the Pod IP if reachable).

Open the dashboard
```http://localhost:8000/ui/```

## Raspbery Pi setup
>Full wiring and audio prep are in [Hardware.md](./docs/Hardware.md). Below are the software steps to call the server.
### 0. Start Pi
```bash
ssh <username>@<hostname>  # ssh mrart@timephone
  or
ssh <username>@<Pi IP Address> # ssh mrart@192.168.0.153
# enter your password
```


### 1. Get the code & tools
```bash
# on the Pi
sudo apt update
sudo apt install -y sox libsox-fmt-all curl jq

# clone the repo
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/mr-Arturio/time-travel-phone.git
cd time-travel-phone/pi-client

# quick checks
sox --version
curl --version
```

### 2. Point the Pi at your laptop (tunneled API)
>Find your **laptop’s LAN IP**, e.g. `192.168.0.155:`
```bash
export CONVERSE_URL="http://192.168.0.155:8000/converse"
export EVENTS_BASE="http://192.168.0.155:8000"   # optional, to post client events
```
Verify reachability:
```bash
curl -s http://192.168.0.155:8000/health | jq
# Expect "ok": true
```

### 3. Sync demo sounds
```bash
chmod +x ~/projects/time-travel-phone/pi-client/bin/sync_sounds.sh
./bin/sync_sounds.sh
```
### 4. Run the phone client
```
/projects/time-travel-phone/pi-client $ ./phone.py
```
**Try it live:**
- Lift handset → you’ll hear dial tone
- Dial 314 → ringback → short greeting → ask Einstein a question → filler
- Hear the reply played through the handset

#### Tiny desktop tester (no Pi)
```powershell
# On Windows (Python 3.8)
py -3.8 .\tiny_client\client.py
# speaks, sends to /converse, and plays reply.wav
```

### Daily start (after first setup)
```bash
# on the pod / server
cd /time-travel-phone/ai-server
bash env.auto.sh             # sets caches/TMP to /workspace (or $HOME)
./start_vllm.sh              # vLLM on :8011
./start_api.sh               # FastAPI on :8000

```
Open the tunnel from your laptop (as above), then run the Pi client.
___
### Dachboard
- URL: http://localhost:8000/ui/
- Shows status (LLM endpoint/model, Whisper device, Piper path)
- Live events via SSE: phone_start, stt_start/done, llm_start/done, tts_start/done, call_end
- Groups by call ID, shows transcript/response preview and timings


## Roadmap
- More personas (Newton, Curie, Lincoln)
- “School/Museum” mode (allowlist + time limits)
- Barge-in (interrupt TTS when user starts speaking)
- Style presets (gentle/professor/excited)
- Optional LoRA adapters and prompt librarie

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
