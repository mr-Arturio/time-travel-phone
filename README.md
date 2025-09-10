
Architecture
Raspberry Pi 4 installed in the old rotarry phone

Speech‑to‑Text: faster‑whisper (CPU by default; leverages CUDA when present)

LLM: vLLM serving openai/gpt-oss-20b (OpenAI API shim)

Text‑to‑Speech: Piper ONNX voice en_US-amy-low.onnx

API: FastAPI routes for /converse, /health, /events; personas via personas.json

Dashboard: /ui static page consuming SSE events to visualize call lifecycle

Run:

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
```
ssh <username>@<hostname>  # ssh mrart@timephone
  or
ssh <username>t@<Pi IP Address> # ssh mrart@192.168.0.153
```
 - enter your password   
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
# export CONVERSE_URL="http://192.168.0.155:8000/converse"


Dashboard: http://localhost:8000/ui/