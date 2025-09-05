from gpiozero import Button
from signal import pause

# Your wiring: F -> GND, L1 -> (1kΩ) -> GPIO17, plus 0.1uF from GPIO17->GND
# Note: Debounce bumped to 50 ms to tame mechanical chatter.
hook = Button(17, pull_up=True, bounce_time=0.05)

def handset_on_cradle():
    print("Handset ON cradle")     # switch closed to GND

def handset_lifted():
    print("Handset LIFTED")        # switch open (pulled up)

# Because the wiring is inverted, pressed == LIFTED and released == ON CRADLE
hook.when_pressed  = handset_lifted
hook.when_released = handset_on_cradle

print("Hook test running... Lift and replace the handset. Press Ctrl+C to quit.")
print("Initial state:", "Handset LIFTED" if hook.is_pressed else "Handset ON cradle")
pause()