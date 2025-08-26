Run:
Connect to your pod using SSH
git clone if needed/pull - git clone https://github.com/mr-Arturio/time-travel-phone.git
cd into
chmod +x run.sh      # only needed first time
./run.sh

On laptop: powershell -ExecutionPolicy Bypass -File .\start-time-travel.ps1


On laptop (new window): py -3.8 tiny_client/client.py

On the fresh pod to install Piper:
chmod +x install-piper.sh
./install-piper.sh
