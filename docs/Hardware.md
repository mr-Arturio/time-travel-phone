Instruction on How to Connect Rotary Phone with Raspbbery Pi 4


List of parts
Rotary Phone Northern Telecom
Raspberry Pi 4B Starter Kit with 4 GB
Assembled Pi Cobbler Plus - Breakout Cable for Raspberry Pi A+/B+/Pi 2/Pi 3
Set of Jumper Cable - at least 10
Resistor 1K OHM 1/4W 5% AXIAL - you will need 2, take pack of 10 they are less then 2 CAD
Half-size 400-Pin DIY Breadboard
USB external sound card audio adapter - USB to Audio Jack Adapter
 0.1 µF ceramic capacitors ×2 they were out of stock i took Polypropylene Film Capacitors. 0.1 µF
 Erbuds with mic and jack

Tools:
Digital Multimeter
Zip ties
Heat Shrink Pack + lighter
two sided stick tape
scredriver
multitool or something that you can clean the wires
Tape
PlayDoh


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