Run:

## Fresh Pod:
```
# Pod shell
git clone https://github.com/mr-Arturio/time-travel-phone.git
cd time-travel-phone/ai-server

chmod +x install-piper.sh install-llm.sh env.auto.sh start_vllm.sh start_api.sh run.sh

# One-time installs
./install-piper.sh
./install-llm.sh

# Start vLLM (8011) – uses env.auto.sh internally
./start_vllm.sh

# Verify vLLM is up
curl -s http://127.0.0.1:8011/v1/models | head -c 200; echo

# First time only: set up venv + deps
./run.sh    # (creates venv, installs requirements, then starts API on :8000)
# ^ If you prefer keeping run.sh only for installs, Ctrl+C and then:
# ./start_api.sh   # start API with env.auto.sh sourced
                 
```
Open tunnel in a new tab:
ssh -i $env:USERPROFILE\.ssh\id_ed25519 `
    -p <podPort> `
    -L 8000:127.0.0.1:8000 `
    -L 8011:127.0.0.1:8011 `
    root@<podIP>

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
ssh <username>@<hostname> - 
  or
ssh <username>t@<Pi IP Address> 
```
 - enter your password

 ```
sudo apt update
sudo apt install -y sox libsox-fmt-all curl jq
# Quick check
sox --version
curl --version

 ```

## For the Hook
Do this (Pi power OFF):
- White wire → GND row on the Cobbler (not the rail):
Find a T-Cobbler pin labeled GND. Put the F wire into the same 5-hole row as that GND pin (so F is directly on ground). Do not use the +/– rails for this step.
- Black wire + 1 kΩ → #13 row (- or any #number, inner rows only, ):
- Pick any empty inner row (not the rails). Put Black in one hole of that row.
- Put one leg of the 1 kΩ resistor in the same row as Black (so Black and that leg touch electrically).
- Put the other leg of the resistor in the row that lines up with #13 on the T-Cobbler (GPIO13). Make sure it’s the same side of the trench as the label.
- Capacitor 0.1 µF from #13 row → any GND row:
- One leg of the cap into the #13 row.
- The other leg into a GND row (you can use the same GND row you used for White).
```
Black ── 1kΩ ──> (row of #13)
                   |
                 0.1µF
                   |
                 (GND row)
White  ───────────────────────────────────────────────> (GND row)
```

## For the Dial
- Blue wire into the  GND row on the Cobbler
- Choose an empty inner row (not the long +/– rails).
- Insert Green into that row.
- Insert one leg of a 1 kΩ resistor into that same row (so Green and that resistor leg are tied together).
- Find #20 (or any #number) on the Cobbler
- Bend and insert the other leg of the resistor into the row that lines up with #20 (or any #number).
- Take a 0.1 µF (“104”) capacitor.
- Put one leg in the #20 row. - or any #number
- Put the other leg in any GND row .

```
Blue ────────────────────────────────> [GND row with a T-Cobbler GND pin]

Green ──[1 kΩ]──> [#20 row on T-Cobbler]
                          │
                      [0.1 µF]
                          │
                        [GND row]
```