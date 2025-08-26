Run:
Connect to your pod using SSH
git clone if needed/pull - git clone https://github.com/mr-Arturio/time-travel-phone.git
cd into time-travel-phone/ai-server
install Piper:
chmod +x install-piper.sh
./install-piper.sh

chmod +x run.sh      # only needed first time
./run.sh

ssh -i $env:USERPROFILE\.ssh\id_ed25519 -p 36964 -L 8000:127.0.0.1:8000 root@213.173.107.140



On laptop: 

Check the poPort - $podPort in start-time-travel.ps1
powershell -ExecutionPolicy Bypass -File .\start-time-travel.ps1


On laptop (new window): py -3.8 tiny_client/client.py

