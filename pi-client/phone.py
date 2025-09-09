#!/usr/bin/env python3
import os, time, signal, subprocess, threading
from gpiozero import Button

# ====== CONFIG ======
HOOK_GPIO = 13
DIAL_GPIO = 20
USB_DEV   = "plughw:CARD=Audio,DEV=0"   # your MOSWAG (change if needed)
SOUNDS    = os.path.expanduser("~/timephone/sounds")
SERVER    = os.environ.get("CONVERSE_URL", "http://127.0.0.1:8000/converse")
# Map 3-digit codes to persona names your server expects
PERSONAS  = {"314":"einstein", "186":"lincoln", "168":"newton"}  # example
INTER_DIGIT_GAP = 0.7      # s of silence between digits
MAX_RECORD_SEC  = 30       # safety cap if no silence
# ====================

# GPIO setup
hook = Button(HOOK_GPIO, pull_up=True, bounce_time=0.01)
dial = Button(DIAL_GPIO, pull_up=True, bounce_time=0.002)

# State
digits = ""
flush_timer = None
first_pulse_seen = False
current_audio = None
recording_proc = None
lock = threading.Lock()

def play_wav(path, loop=False):
    """Start aplay in the background; return Popen handle."""
    args = ["aplay", "-q", "-D", USB_DEV, path]
    if loop:
        # crude loop: respawn in a thread
        def loop_play():
            while True:
                p = subprocess.Popen(args)
                rc = p.wait()
                if rc != 0: break
                # tiny pause to avoid clicks
                time.sleep(0.05)
        t = threading.Thread(target=loop_play, daemon=True)
        t.start()
        return None
    else:
        return subprocess.Popen(args)

def stop_playing():
    global current_audio
    # aplay we spawn non-looping; for looping we didn't keep a handle
    # kill any aplay processes just in case
    subprocess.call(["pkill", "-f", "aplay -q -D " + USB_DEV])
    current_audio = None

def schedule_flush():
    global flush_timer
    if flush_timer:
        flush_timer.cancel()
    flush_timer = threading.Timer(INTER_DIGIT_GAP, flush_digit)
    flush_timer.daemon = True
    flush_timer.start()

def flush_digit():
    global digits, flush_timer
    with lock:
        if flush_timer:
            flush_timer = None
        # nothing to do if no pulses accumulated yet
        return

def on_dial_pulse():
    """Count 'open' pulses as digit ticks."""
    global first_pulse_seen, digits
    with lock:
        if not first_pulse_seen:
            first_pulse_seen = True
            stop_playing()  # stop dial tone on first pulse
        # accumulate a 'tick' by using a placeholder; we convert to digit on flush
        digits += "x"
        schedule_flush()

def finalize_digit():
    """Convert accumulated ticks to a digit string '0'-'9'."""
    global digits
    n = len(digits)
    digits = ""
    if n == 0: return None
    d = 0 if n == 10 else n
    return str(d)

def wait_for_digit():
    """Wait until the inactivity timer fires, then return the completed digit."""
    # Poll for when flush_timer becomes None *after* a pulse happened
    while True:
        time.sleep(0.05)
        with lock:
            # if we saw pulses and timer expired -> a digit is ready
            if 'x' not in digits and flush_timer is None:
                # no pulses pending -> means previous digit should have finalized already
                return None
            # timer expired will be handled by checking tick count drop; simpler path:
        # Slightly different approach: we check for no pulses in last INTER_DIGIT_GAP
        # We'll rely on the main loop to call finalize when gap detected.
        # (See main loop below)
        # To keep this simple, we'll not use wait_for_digit and do logic inline.
        return None

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
    """Use arecord + sox to stop on ~2s silence and trim."""
    global recording_proc
    stop_playing()
    # arecord from USB, pipe to sox which stops on 2s of <2% amplitude
    cmd = (
        f"arecord -q -D {USB_DEV} -f S16_LE -c1 -r16000 | "
        f"sox -t wav - -t wav {out_wav} silence 1 0.2 2% 1 2.0 2% trim 0 {MAX_RECORD_SEC}"
    )
    recording_proc = subprocess.Popen(cmd, shell=True)
    rc = recording_proc.wait()
    recording_proc = None
    return rc == 0

def converse(persona, in_wav, out_wav):
    """POST to your FastAPI /converse; save reply to out_wav. Falls back to click."""
    try:
        cmd = [
            "curl","-s","-X","POST",
            "-F", f"persona={persona}",
            "-F", f"audio=@{in_wav};type=audio/wav",
            SERVER, "-o", out_wav
        ]
        rc = subprocess.call(cmd)
        if rc != 0 or not os.path.exists(out_wav) or os.path.getsize(out_wav) < 44:
            raise RuntimeError("server failed")
        return True
    except Exception:
        # fallback: just a click
        subprocess.call(["cp", os.path.join(SOUNDS,"click.wav"), out_wav])
        return True

def reset_call_state():
    global digits, flush_timer, first_pulse_seen
    digits = ""
    first_pulse_seen = False
    if flush_timer:
        flush_timer.cancel()
        flush_timer = None

def on_hook_up():
    # Handset lifted: start dial tone and get ready to collect digits
    reset_call_state()
    print("[HOOK] LIFTED")
    start_dial_tone()

def on_hook_down():
    # Handset on cradle: stop everything
    print("[HOOK] ON cradle")
    stop_playing()
    if recording_proc:
        try: recording_proc.terminate()
        except Exception: pass
    reset_call_state()

def main():
    print("TimePhone ready. Lift handset and dial a 3-digit code (e.g., 314). Ctrl+C to quit.")
    hook.when_released = on_hook_up      # lift
    hook.when_pressed  = on_hook_down    # hang
    dial.when_released = lambda: on_dial_pulse()

    try:
        while True:
            time.sleep(0.05)
            # If we have pulses and no new pulses for INTER_DIGIT_GAP -> finalize digit
            # Implement by tracking last change time:
            # Simpler: after each 50ms tick, check and finalize using a small buffer.
            pass
    except KeyboardInterrupt:
        on_hook_down()

if __name__ == "__main__":
    # Replace the minimal event loop with a clearer finite-state loop:
    last_count = 0
    last_change = time.time()
    hook.when_released = on_hook_up
    hook.when_pressed  = on_hook_down
    dial.when_released = lambda: (
        [globals().__setitem__('last_change', time.time()),
         globals().__setitem__('last_count', last_count+1),
         on_dial_pulse()][-1]
    )

    print("TimePhone ready. Lift handset and dial a 3-digit code (e.g., 314). Ctrl+C to quit.")
    try:
        while True:
            time.sleep(0.05)
            # handle inter-digit gap
            if first_pulse_seen:
                if time.time() - last_change >= INTER_DIGIT_GAP and last_count > 0:
                    n = last_count
                    last_count = 0
                    d = 0 if n == 10 else n
                    # append digit
                    with lock:
                        code = "".join([])  # unused
                    digits_str = ("" if not hasattr(main, 'digits_str') else main.digits_str)
                    digits_str += str(d)
                    main.digits_str = digits_str
                    print(f"[DIAL] Digit: {d}  (code so far: {digits_str})")

                    # stop dial tone on first digit (already stopped on first pulse, but safe)
                    stop_playing()

                    # If 3 digits collected -> place "call"
                    if len(digits_str) == 3:
                        code = digits_str
                        main.digits_str = ""  # reset for next time

                        persona = PERSONAS.get(code, "einstein")
                        print(f"[CALL] Connecting to {persona} ({code})…")

                        # ringback for ~6s (2 cycles)
                        ringback_for(6)

                        # little "answer click"
                        play_wav(os.path.join(SOUNDS, "click.wav"))
                        time.sleep(0.1)
                        stop_playing()

                        # Record question until ~2s silence
                        qwav = os.path.expanduser("~/timephone/question.wav")
                        rwav = os.path.expanduser("~/timephone/reply.wav")
                        print("[REC] Ask your question… (stops after ~2s silence)")
                        record_until_silence(qwav)

                        # If hung up mid-record, abort
                        if hook.is_pressed:  # pressed = on cradle
                            print("[HOOK] Hung up during record; aborting.")
                            stop_playing()
                            reset_call_state()
                            continue

                        # Send to server & play reply
                        print("[LLM] Sending to server…")
                        ok = converse(persona, qwav, rwav)
                        if ok and not hook.is_pressed:
                            print("[PLAY] Reply…")
                            p = play_wav(rwav)
                            if p: p.wait()
                        stop_playing()
                        reset_call_state()

                # If handset goes down, on_hook_down() cleared state
    except KeyboardInterrupt:
        on_hook_down()
