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


```
L1 ── 1kΩ ──> (row of #17)
                   |
                 0.1µF
                   |
                 (GND row)
F  ───────────────────────────────────────────────> (GND row)
```
## For the Hook
Do this (Pi power OFF):
- F → GND row on the Cobbler (not the rail):
Find a T-Cobbler pin labeled GND. Put the F wire into the same 5-hole row as that GND pin (so F is directly on ground). Do not use the +/– rails for this step since you don’t have jumpers.
- L1 + 1 kΩ → #17 row (inner rows only):
- Pick any empty inner row (not the rails). Put L1 in one hole of that row.
- Put one leg of the 1 kΩ resistor in the same row as L1 (so L1 and that leg touch electrically).
- Put the other leg of the resistor in the row that lines up with #17 on the T-Cobbler (GPIO17). Make sure it’s the same side of the trench as the label.
- Capacitor 0.1 µF from #17 row → any GND row:
- One leg of the cap into the #17 row.
- The other leg into a GND row (you can use the same GND row you used for F).

## For the Dial
- Dial_B wire into the  GND row on the Cobbler
- Choose an empty inner row (not the long +/– rails).
- Insert Dial_A into that row.
- Insert one leg of a 1 kΩ resistor into that same row (so Dial_A and that resistor leg are tied together).
- Find #27 on the Cobbler
- Bend and insert the other leg of the resistor into the row that lines up with #27.
- Take a 0.1 µF (“104”) capacitor.
- Put one leg in the #27 row.
- Put the other leg in any GND row .

```
Dial_B ────────────────────────────────> [GND row with a T-Cobbler GND pin]

Dial_A ──[1 kΩ]──> [#27 row on T-Cobbler]
                          │
                      [0.1 µF]
                          │
                        [GND row]
```