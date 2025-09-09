#!/usr/bin/env python3
import os, time, subprocess, threading, signal
from threading import Timer
from gpiozero import Button

# ====== CONFIG ======
HOOK_GPIO = 13                 # <-- your wiring
DIAL_GPIO = 20                 # <-- your wiring
USB_DEV   = "plughw:CARD=Audio,DEV=0"   # your MOSWAG
SOUNDS    = os.path.expanduser("~/timephone/sounds")
SERVER    = os.environ.get("CONVERSE_URL", "http://127.0.0.1:8000/converse")
PERSONAS  = {"314":"einstein", "186":"lincoln", "168":"newton"}  # example codes
INTER_DIGIT_GAP = 0.70         # seconds of silence to mark end-of-digit
MAX_RECORD_SEC  = 30           # safety cap
# ====================

# GPIO setup
hook = Button(HOOK_GPIO, pull_up=True,  bounce_time=0.01)
dial = Button(DIAL_GPIO,  pull_up=True,  bounce_time=0.002)  # "open" pulses while dial returns

# State
digits_str = ""
first_pulse_seen = False
pulse_count = 0
flush_timer: Timer | None = None
recording_proc: subprocess.Popen | None = None
state_lock = threading.Lock()

def play_wav(path, loop=False):
    """Play WAV to USB sound card. If loop=True, respawn forever in a daemon thread."""
    args = ["aplay", "-q", "-D", USB_DEV, path]
    if loop:
        def looper():
            while True:
                p = subprocess.Popen(args)
                rc = p.wait()
                if rc != 0:
                    break
                time.sleep(0.05)
        t = threading.Thread(target=looper, daemon=True)
        t.start()
        return None
    else:
        return subprocess.Popen(args)

def stop_playing():
    # Kill any aplay session going to our device
    subprocess.call(["pkill", "-f", f"aplay -q -D {USB_DEV}"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def start_dial_tone():
    stop_playing()
    play_wav(os.path.join(SOUNDS, "dial_tone.wav"), loop=True)

def ringback_for(seconds=6):
    stop_playing()
    end = time.time() + seconds
    while time.time() < end:
        p = play_wav(os.path.join(SOUNDS, "ringback.wav"))
        if p: p.wait()

def record_until_silence(out_wav):
    """Record mic and stop ~2s after silence using sox."""
    global recording_proc
    stop_playing()
    cmd = (
        f"arecord -q -D {USB_DEV} -f S16_LE -c1 -r16000 | "
        f"sox -t wav - -t wav {out_wav} silence 1 0.2 2% 1 2.0 2% trim 0 {MAX_RECORD_SEC}"
    )
    recording_proc = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid)
    recording_proc.wait()
    recording_proc = None

def converse(persona, in_wav, out_wav):
    """POST to FastAPI /converse; save reply to out_wav. Fallback to click if it fails."""
    try:
        rc = subprocess.call([
            "curl","-s","-X","POST",
            "-F", f"persona={persona}",
            "-F", f"audio=@{in_wav};type=audio/wav",
            SERVER, "-o", out_wav
        ])
        if rc != 0 or not os.path.exists(out_wav) or os.path.getsize(out_wav) < 44:
            raise RuntimeError("server failed")
        return True
    except Exception:
        # Fallback: a tiny click if server unreachable
        subprocess.call(["cp", os.path.join(SOUNDS, "click.wav"), out_wav])
        return True

def cancel_flush_timer():
    global flush_timer
    if flush_timer:
        try: flush_timer.cancel()
        except: pass
        flush_timer = None

def schedule_flush():
    """Restart the inter-digit inactivity timer."""
    global flush_timer
    cancel_flush_timer()
    flush_timer = Timer(INTER_DIGIT_GAP, finalize_digit)
    flush_timer.daemon = True
    flush_timer.start()

def reset_call_state():
    global digits_str, first_pulse_seen, pulse_count
    cancel_flush_timer()
    digits_str = ""
    first_pulse_seen = False
    pulse_count = 0

def on_hook_up():
    # Lift handset: start fresh & play dial tone
    print("[HOOK] LIFTED")
    reset_call_state()
    start_dial_tone()

def on_hook_down():
    # Handset on cradle: stop audio, stop any recording, clear state
    print("[HOOK] ON cradle")
    stop_playing()
    if recording_proc:
        try:
            os.killpg(os.getpgid(recording_proc.pid), signal.SIGTERM)
        except Exception:
            pass
    reset_call_state()

def on_dial_pulse():
    """Count the 'open' pulses from the rotary dial as it returns."""
    global first_pulse_seen, pulse_count
    with state_lock:
        if not first_pulse_seen:
            first_pulse_seen = True
            stop_playing()  # stop dial tone on the very first pulse
        pulse_count += 1
        schedule_flush()

def finalize_digit():
    """Called after INTER_DIGIT_GAP of no pulses; turns pulses→digit and acts on 3rd digit."""
    global pulse_count, digits_str
    with state_lock:
        n = pulse_count
        pulse_count = 0
    if n == 0:
        return
    d = 0 if n == 10 else n
    digits_str += str(d)
    print(f"[DIAL] Digit: {d}  (code so far: {digits_str})")

    # If we have three digits, place the "call"
    if len(digits_str) == 3:
        code = digits_str
        reset_call_state()  # ready for next call after we finish
        persona = PERSONAS.get(code, "einstein")
        print(f"[CALL] Connecting to {persona} ({code})…")

        # Ringback then "answer click"
        ringback_for(6)
        p = play_wav(os.path.join(SOUNDS, "click.wav"))
        if p: p.wait()
        stop_playing()

        # Record the question until ~2s of silence
        qwav = os.path.expanduser("~/timephone/question.wav")
        rwav = os.path.expanduser("~/timephone/reply.wav")
        print("[REC] Ask your question… (stops ~2s after silence)")
        record_until_silence(qwav)

        # If hung up during record, abort quietly
        if hook.is_pressed:  # pressed = ON cradle
            print("[HOOK] Hung up during record; abort.")
            stop_playing()
            reset_call_state()
            return

        # Send to LLM server & play reply
        print("[LLM] Sending to server…")
        ok = converse(persona, qwav, rwav)
        if ok and hook.is_pressed:
            print("[PLAY] Reply…")
            p = play_wav(rwav)
            if p: p.wait()
        stop_playing()
        # leave line quiet until next lift/hang cycle

def main():
    hook.when_pressed = on_hook_up     # lift
    hook.when_released  = on_hook_down   # hang
    dial.when_released = on_dial_pulse  # count "open" pulses
    print("TimePhone ready. Lift handset and dial a 3-digit code (e.g., 314). Ctrl+C to quit.")
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        on_hook_down()

if __name__ == "__main__":
    main()
