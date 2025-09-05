from gpiozero import Button
from signal import pause
import time

# Dial pulses are normally-closed to GND and "open" as the dial returns.
# Wiring: Dial_B -> GND, Dial_A -> (1k) -> GPIO27, plus 0.1uF from GPIO27->GND
dial = Button(27, pull_up=True, bounce_time=0.002)  # 2 ms software debounce

digit = 0
last  = time.time()

def flush():
    global digit
    if digit:
        print("Digit:", 0 if digit == 10 else digit)
        digit = 0

def on_open_pulse():  # count when the contact OPENS
    global digit, last
    now = time.time()
    if now - last > 0.6:   # gap between digits (~>600 ms works well)
        flush()
    digit += 1
    last = now

dial.when_released = on_open_pulse  # count the "open" pulses
print("Dial test: lift the handset and dial a few numbers. Ctrl+C to quit.")
pause()

