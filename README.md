Run:

## Fresh Pod:
```
Connect to your pod using SSH
git clone https://github.com/mr-Arturio/time-travel-phone.git
cd time-travel-phone/ai-server
chmod +x install-piper.sh
./install-piper.sh           # one-time Piper build + voice
chmod +x install-llm.sh         # one-time vLLM install into venv
chmod +x run.sh
./run.sh                     # one-time deps + sanity (or just: pip install -r requirements.txt)
```
Open tunnel in a new tab:
ssh -i $env:USERPROFILE\.ssh\id_ed25519 -p 40661 -L 8000:127.0.0.1:8000 root@213.173.107.140

curl http://localhost:8000/health

On laptop tab: 

Check and update the poPort - $podPort in start-time-travel.ps1
powershell -ExecutionPolicy Bypass -File .\start-time-travel.ps1


On laptop (new window): py -3.8 C:\Users\mrart\time-travel-phone\tiny_client\client.py


##Daily start
```
cd /time-travel-phone/ai-server
bash env.auto.sh             # sets caches/TMP to /workspace (or $HOME)
./start_vllm.sh              # brings up vLLM on :8011
./start_api.sh               # brings up FastAPI on :8000

```