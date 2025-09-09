#!/usr/bin/env python3
from gpiozero import Button
from signal import pause

# HOOK on GPIO13 (your wiring). F->GND, L1->(1k)->GPIO13, +0.1uF GPIO13->GND
hook = Button(13, pull_up=True, bounce_time=0.01)

def on_down():
    print("Handset ON cradle")

def on_up():
    print("Handset LIFTED")

# If messages look reversed for your contact pair, just swap these two lines:
hook.when_pressed  = on_down     # pressed = closed to GND (on cradle)
hook.when_released = on_up       # released = open (lifted)

print("Hook test running... Lift/hang a few times. Ctrl+C to quit.")
pause()

