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


## Fresh Pod:
```
git clone https://github.com/mr-Arturio/time-travel-phone.git
cd time-travel-phone/ai-server
chmod +x install-piper.sh
./install-piper.sh           # one-time Piper build + voice
chmod +x ../install-llm.sh 2>/dev/null || true
../install-llm.sh            # one-time vLLM install into venv
chmod +x run.sh
./run.sh                     # one-time deps + sanity (or just: pip install -r requirements.txt)
```

##Daily start
```
cd /time-travel-phone/ai-server
bash env.auto.sh             # sets caches/TMP to /workspace (or $HOME)
./start_vllm.sh              # brings up vLLM on :8011
./start_api.sh               # brings up FastAPI on :8000

```