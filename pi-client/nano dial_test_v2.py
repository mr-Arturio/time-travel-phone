from gpiozero import Button
from threading import Timer
from signal import pause

# Wiring recap:
# HOOK: F -> GND, L1 -> (1k) -> GPIO17, + 0.1uF GPIO17->GND
# DIAL: Dial_B -> GND, Dial_A -> (1k) -> GPIO27, + 0.1uF GPIO27->GND

hook = Button(17, pull_up=True, bounce_time=0.01)
dial = Button(27, pull_up=True, bounce_time=0.002)  # 2 ms; adjust if needed

digit = 0
flush_timer = None
INTER_DIGIT_GAP = 0.7  # seconds of silence to consider digit complete

def flush():
    global digit, flush_timer
    if digit:
        print("Digit:", 0 if digit == 10 else digit)
        digit = 0
    flush_timer = None

def schedule_flush():
    global flush_timer
    if flush_timer:
        flush_timer.cancel()
    flush_timer = Timer(INTER_DIGIT_GAP, flush)
    flush_timer.daemon = True
    flush_timer.start()

# Count pulses on "open" as the dial returns
def on_pulse():
    global digit
    digit += 1
    schedule_flush()

# Nice UX: print hook state and make sure any partial digit is flushed on hang-up
def on_hook_down():
    flush()
    print("Handset ON cradle")

def on_hook_up():
    print("Handset LIFTED")

dial.when_released = on_pulse
hook.when_pressed  = on_hook_down     # switch closed to GND
hook.when_released = on_hook_up       # switch open (pulled up)

print("Dial test v2: lift handset and dial. Ctrl+C to quit.")
pause()
