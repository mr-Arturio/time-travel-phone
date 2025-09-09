import os, time, subprocess, threading, signal, requests
from threading import Timer
from gpiozero import Button

# ====== CONFIG ======
HOOK_GPIO = 13                 # <-- your wiring
DIAL_GPIO = 20                 # <-- your wiring
USB_DEV   = "plughw:CARD=Audio,DEV=0"   # your MOSWAG
SOUNDS    = os.path.expanduser("~/timephone/sounds")

# API endpoints
SERVER    = os.environ.get("CONVERSE_URL", "http://127.0.0.1:8000/converse")
# Derive base for /event from /converse
SERVER_BASE = os.environ.get("EVENTS_BASE", None)
if not SERVER_BASE:
    SERVER_BASE = SERVER.rsplit("/", 1)[0] if SERVER.endswith("/converse") else SERVER

PERSONAS  = {"314":"einstein", "186":"lincoln", "168":"newton"}  # example codes

INTER_DIGIT_GAP = 0.70         # seconds of silence to mark end-of-digit
MAX_RECORD_SEC  = 30           # safety cap
HOOK_BOUNCE     = 0.15         # debounce for hook GPIO (helps with chatter)
HANGUP_GRACE    = 0.35         # must be ON cradle continuously for this long to count
# ====================

# --- helpers for events → dashboard (/event) ---
def emit(event: str, data: dict | None = None):
    try:
        requests.post(f"{SERVER_BASE}/event", json={"event": event, "data": data or {}}, timeout=1.5)
    except Exception:
        pass

def log(msg: str):
    print(msg, flush=True)

# GPIO setup
hook = Button(HOOK_GPIO, pull_up=True,  bounce_time=HOOK_BOUNCE)
dial = Button(DIAL_GPIO,  pull_up=True,  bounce_time=0.002)  # "open" pulses while dial returns

# Interpret hook.is_pressed == ON cradle (closed to GND)
def hook_on_cradle() -> bool:
    return hook.is_pressed

def hung_up_stable(timeout=HANGUP_GRACE) -> bool:
    """Return True only if hook stays ON CRADLE for the entire timeout window."""
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        if not hook_on_cradle():
            return False
        time.sleep(0.01)
    return True

# State
digits_str = ""
first_pulse_seen = False
pulse_count = 0
flush_timer = None               # type: Timer | None
recording_proc = None            # type: subprocess.Popen | None
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

def ringback_for(seconds=4):
    stop_playing()
    emit("ringback", {"sec": seconds})
    end = time.time() + seconds
    while time.time() < end:
        p = play_wav(os.path.join(SOUNDS, "ringback.wav"))
        if p: p.wait()

def record_until_silence(out_wav):
    """Record mic and stop ~2s after silence using sox. Aborted by on_hook_down() killing the pgid."""
    global recording_proc
    stop_playing()
    cmd = (
        f"arecord -q -D {USB_DEV} -f S16_LE -c1 -r16000 | "
        f"sox -t wav - -t wav {out_wav} silence 1 0.2 2% 1 2.0 2% trim 0 {MAX_RECORD_SEC}"
    )
    # Start in its own process group so we can kill the whole pipeline
    recording_proc = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid)
    recording_proc.wait()
    recording_proc = None

def converse(persona, in_wav, out_wav):
    """POST to FastAPI /converse; save reply to out_wav. Fallback to click if it fails."""
    try:
        log(f"[NET] POST {SERVER}")
        emit("stt_start", {"persona": persona})
        rc = subprocess.call([
            "curl","-s","-X","POST",
            "-F", f"persona={persona}",
            "-F", f"audio=@{in_wav};type=audio/wav",
            SERVER, "-o", out_wav
        ])
        emit("stt_done", {})
        if rc != 0 or not os.path.exists(out_wav) or os.path.getsize(out_wav) < 44:
            raise RuntimeError("server failed")
        # Mirror the server-side phases so the dashboard looks lively
        emit("llm_start", {})
        emit("llm_done", {})
        emit("tts_start", {})
        emit("tts_done", {})
        return True
    except Exception as e:
        log(f"[NET] ERROR posting to server: {e}")
        # Fallback: a tiny click if server unreachable
        subprocess.call(["cp", os.path.join(SOUNDS, "click.wav"), out_wav])
        emit("call_end", {"reason": "net_error"})
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
    log("[HOOK] LIFTED")
    emit("phone_start", {})
    reset_call_state()
    start_dial_tone()

def on_hook_down():
    # Handset on cradle: require stable hang-up to avoid bounce
    if not hung_up_stable():
        log("[HOOK] bounce ignored")
        return
    log("[HOOK] ON cradle")
    stop_playing()
    if recording_proc:
        try:
            os.killpg(os.getpgid(recording_proc.pid), signal.SIGTERM)
        except Exception:
            pass
    emit("call_end", {"reason": "hangup"})
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
    log(f"[DIAL] Digit: {d}  (code so far: {digits_str})")
    emit("dial_digit", {"d": d, "code": digits_str})

    # If we have three digits, place the "call"
    if len(digits_str) == 3:
        code = digits_str
        reset_call_state()  # ready for next call after we finish
        persona = PERSONAS.get(code, "einstein")
        log(f"[CALL] Connecting to {persona} ({code})…")

        # Ringback then "answer click"
        ringback_for(4)
        p = play_wav(os.path.join(SOUNDS, "click.wav"))
        if p: p.wait()
        stop_playing()

        # Record the question until ~2s of silence
        qwav = os.path.expanduser("~/timephone/question.wav")
        rwav = os.path.expanduser("~/timephone/reply.wav")
        log("[REC] Ask your question… (stops ~2s after silence)")
        emit("record_start", {})
        t0 = time.monotonic()
        record_until_silence(qwav)
        dur = round(time.monotonic() - t0, 2)
        emit("record_done", {"sec": dur})

        # If hung up during record (stable), abort quietly
        if hook_on_cradle():
            log("[HOOK] Hung up during record; abort.")
            stop_playing()
            emit("call_end", {"reason": "hangup_during_record"})
            reset_call_state()
            return

        # Send to LLM server & play reply
        log("[LLM] Sending to server…")
        ok = converse(persona, qwav, rwav)
        # Play reply only if handset is STILL lifted
        if ok and not hook_on_cradle():
            log("[PLAY] Reply…")
            p = play_wav(rwav)
            if p: p.wait()
        stop_playing()
        emit("call_end", {"reason": "ok"})
        # leave line quiet until next lift/hang cycle

def main():
    # IMPORTANT: pressed == ON cradle, released == LIFTED
    hook.when_pressed   = on_hook_down   # on-cradle
    hook.when_released  = on_hook_up     # lifted
    dial.when_released  = on_dial_pulse  # count "open" pulses

    log("TimePhone ready. Lift handset and dial a 3-digit code (e.g., 314). Ctrl+C to quit.")
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        on_hook_down()

if __name__ == "__main__":
    main()