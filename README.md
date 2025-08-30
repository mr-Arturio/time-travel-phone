Run:
Connect to your pod using SSH
git clone if needed/pull - git clone https://github.com/mr-Arturio/time-travel-phone.git
cd time-travel-phone/ai-server
install Piper:
chmod +x install-piper.sh
./install-piper.sh

chmod +x run.sh      # only needed first time
./run.sh


ssh -i $env:USERPROFILE\.ssh\id_ed25519 -p 17340 -L 8000:127.0.0.1:8000 root@213.173.107.140

curl http://localhost:8000/health

On laptop: 

Check and update the poPort - $podPort in start-time-travel.ps1
powershell -ExecutionPolicy Bypass -File .\start-time-travel.ps1


On laptop (new window): py -3.8 tiny_client/client.py

cd /time-travel-phone/ai-server
chmod +x install-llm.sh
./install-llm.sh

export VLLM_MODEL="gpt-oss-20B"   # or local path to weights
python -m vllm.entrypoints.openai.api_server \
  --model "$VLLM_MODEL" \
  --host 127.0.0.1 --port 8001

In server.py:

from llm_backends import chat

def persona_reply(name, style, transcript):
    if not transcript:
        return "I didn't catch that. Please repeat."
    system = f"You are {name}. Stay concise, natural, and on-topic. Style: {style}"
    user   = transcript
    try:
        return chat(system, user)
    except Exception:
        # graceful fallback
        return f"{name} here. {clean_and_punctuate(transcript)}"