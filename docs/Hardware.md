# Instructions: How to Connect a Rotary Phone to a Raspberry Pi 4B
_This is my “from-zero” logbook for turning a Northern Telecom rotary phone into a Raspberry-Pi-powered conversation device. It keeps the charm of the old hardware while steering clear of the original ring/line circuitry._

>### ⚠️Safety first
>- **We are not connecting to the public phone network.**
>- **Unplug power whenever you touch GPIO or rewire anything.**
>- **Avoid touching bare pins or the underside of the Pi while powered.**
>- **Old phones can have sticky tar/gel in the 425B block—messy but not toxic.**

### Parts List
- Rotary Phone Northern Telecom
- Raspberry Pi 4B Starter Kit with 4 GB ![Raspberry Pi 4B Starter Kit](./Pi_Kit.jpg)
  - I picked a Raspberry Pi 4B Starter Kit because it’s perfect for first-timers (me). It included:
    - Pi 4B (4 GB RAM)
    - Case
    - 5.1V/3A USB-C power supply
    - 32 GB microSD with Raspberry Pi OS pre-flashed
    - HDMI A→Micro-D cable
    - USB microSD reader
    - Heatsinks
    - Quick-start guide
- Assembled Pi Cobbler Plus - Breakout Cable for Raspberry Pi A+/B+/Pi 2/Pi 3
- Set of Jumper Cable - at least 10
- Resistor 1K OHM 1/4W 5% AXIAL - you will need 2, take pack of 10 they are less then 2 CAD
- Capacitors 0.1 µF (x2) — I used polypropylene film (ceramic is fine)
- Half-size 400-Pin DIY Breadboard
- USB external sound card audio adapter - USB to Audio Jack Adapter
![](./SoundCard.jpg)
- Erbuds with mic and jack

Tools (what I actually used):
- Digital Multimeter
![](./Multimeter.jpg)
- Screwdriver, nippers, pliers, small multitool (for cleaning wire ends)
![](./tools.jpg)
- Heat Shrink Pack + lighter
- Zip ties
- Mounting tape
- Drill + bits
- Tape
- Play-Doh (yes, your kids 'modeling compound' -)
- Nice-to-have (I didn’t have them this time): Alligator Clip Multimeter Leads
![Alligator Clip](./Alligato_clips.jpg)

## Step 1 — Open the phone & explore
![](./without_shell.jpg)
- remove the shell, get familiar with phone structure - how cardle works and how its get activated, garb multimeter and play around, understand what connect where, hear the beep, 
- use NEt 425B block to find nececcery wires - we need two from dial and two from cradle
- re,ove handle - ear peace? out the way by 
- remove Ring (bells) block - leave if you are planning to use it - make phone ring - immiting reciving calls
- unscrew dial, get familiar with the cunstruction, see the mechanics how it works
- you will see 4 wires coming out from dial - two for dialing the number, 2 for preventin mic work and noise whr diaking in process
we need to grab 2 that resmonsible for dialing in my case it is blue and green
to check them use multimeter, tuch each wire in continuity test mode and dial the number you will hear beep with pauses equel to the number dialed - connection on and off. If you hear long beep withourt pauses - like me -your multimeter is not fat enogh to react to these interupted signals. What i did - i dialed a number and did not relesed it but slowly moved it with my hand - you will hear beeps equls to numvber dialed. it may rerquire some specific hand gymnastics. Thats where this alligator clips will be handy - i wish i got them 
- when you found the wires responsible for dialind mark them, other two you can leave - you can use them for some additional logic - like play dialing sound - isolate the ends that they did not short, fold, tape, put out the way
- now to locate the cradle wires:  locate all wires coming of cradle mechanism, see where they connect to NEt 425B block. With multimeter find 2 that responsible for cradle. Cradle on - no signal, cardle lift long signal. mark them
- uscrew/cut all the wires from NEt 425B block
- now yu can remove NEt 425B block - i spend some time doind it, it got messy becouse the is some gue inside this block, nothing toxic or dangerous just too sticky, so i recoment to try and to drill out two pins on the buttom of the fnone that holds the block.I ended up removing the iner part of NEt 425B block, get myself and all around in this yacky vaselin-glue thing, ascking GPT to how to clean it from my hads (use WD-40 and dish soap), after i got this shell of NEt 425B block - i swing it back and force with Pliers, removed it and there was a metall thing underneth that i  ended up removing with the drill... So just try to trill it out from the back of phone - see image
- You should have clear phone base with wires comming from cradle adn 4 wires from dial

Step 2
![](./pi_schema.jpg)
- Download Raspberry Pi Imager - https://www.raspberrypi.com/software/
- Here i the clear [Getting Started](https://www.raspberrypi.com/documentation/computers/getting-started.html) instruction with all the required steps and how to [Install an operation system](https://www.raspberrypi.com/documentation/computers/getting-started.html#installing-the-operating-system) and setup the WiFi connection. Just make sure that you have no other memory cards or any other storage devices connected - to avoid accidentace removal all the information from them. 
- Istall sD card intom Pi, power it up. And try to connect to it through your terminal -- `ssh <username>@<hostname>` or `ssh <username>@<Pi IP Address>`. If you failed to connect with hostname - try Pi IP Adress to find it:  to login to your wifi aadmin page -informationcan be found at the back of your wifi, and find if the system sees your Pi as connected devices - Host name will be sameas you provided during instalation. and there you can find Ip Address. Here is detailed (Configuration on first boot)[https://www.raspberrypi.com/documentation/computers/getting-started.html#configuration-on-first-boot] instructions with troubleshooting. If its not there, First try to unplu and plug bsck you Pi, wait a minute till the green light stop blinking on the Pi and ttry again, if still no go - i recomended to reinstall operation system ance again,  take out sD card - inserd into your laptop and lunch Imager once again, fill up WiFi name and password with caution foloww insrtructions afte rsucessful instalatiuon inser sD card back to Pi - powe rit up, give it few minutes and try terminal again, after succesfull conectuion it will ask you to type the password - and you are connected.
If still it could not comnnect to WiFi - use Ethernet connection if available, and check your intterne Admin page ance again to see the Pi connected. If still not suceeded, you can connect monitore with provided cable from the kit, connect keyboard and mouse and astr Pi and you will see operation system refer to (Configuration on first boot)[https://www.raspberrypi.com/documentation/computers/getting-started.html#configuration-on-first-boot] instructions.
Cangrats! Your Pi is up and running!
**Avoid holding the board or touching GPIO pins** when the board is powered. Shorting the pins can easily damage the board, rendering it unusable.

Step 3 wiring
- connect T Cobbler to the Pi
![]()

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

### What’s next
Once the hardware is solid, jump to the project [README](../README.md) for software bring-up:
- Server (FastAPI + Whisper + vLLM + Piper)
- Pi client app (dial tone, ringback, recording, posting to /converse)
- Dashboard at /ui to watch events (SSE)

Enjoy! <br>
PS: I wish I took more photos while building(