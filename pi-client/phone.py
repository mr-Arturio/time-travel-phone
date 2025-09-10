#!/usr/bin/env python3
import os, time, subprocess, threading, signal, requests, shlex, random
from threading import Timer
from gpiozero import Button

# ====== CONFIG ======
HOOK_GPIO = 13
DIAL_GPIO = 20
USB_DEV   = "plughw:CARD=Audio,DEV=0"
SOUNDS    = os.path.expanduser("~/timephone/sounds")

SERVER    = os.environ.get("CONVERSE_URL", "http://127.0.0.1:8000/converse")
SERVER_BASE = os.environ.get("EVENTS_BASE", None)
if not SERVER_BASE:
    SERVER_BASE = SERVER.rsplit("/", 1)[0] if SERVER.endswith("/converse") else SERVER

PERSONAS  = {"314":"einstein", "186":"lincoln", "168":"newton"}

INTER_DIGIT_GAP = 0.70
MAX_RECORD_SEC  = 30
HOOK_BOUNCE     = 0.15
HANGUP_GRACE    = 0.35
# ====================

ARECORD_PAT = f"arecord -q -D {USB_DEV}"
SOX_PIPE_PAT = "sox -t wav - -t wav"

def emit(event: str, data: dict | None = None):
    try:
        requests.post(f"{SERVER_BASE}/event", json={"type": event, "data": data or {}}, timeout=1.5)
    except Exception:
        pass

def log(msg: str):
    print(msg, flush=True)

hook = Button(HOOK_GPIO, pull_up=True,  bounce_time=HOOK_BOUNCE)
dial = Button(DIAL_GPIO,  pull_up=True,  bounce_time=0.002)

def hook_on_cradle() -> bool:
    return not hook.is_pressed

def hung_up_stable(timeout=HANGUP_GRACE) -> bool:
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        if not hook_on_cradle():
            return False
        time.sleep(0.01)
    return True

# ---- state ----
digits_str = ""
first_pulse_seen = False
pulse_count = 0
flush_timer = None
recording_proc = None
state_lock = threading.Lock()

# ---- helpers: audio play/stop ----
def play_wav(path, loop=False):
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

def play_wav_for(path, seconds: float):
    secs = max(0.1, float(seconds))
    cmd = (
        f"sox {shlex.quote(path)} -t wav - trim 0 {secs} | "
        f"aplay -q -D {USB_DEV} -t wav -"
    )
    return subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid)

def stop_playing():
    # stop any aplay (and filler) quickly
    subprocess.call(["pkill", "-f", f"aplay -q -D {USB_DEV}"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # also stop any sox→aplay pipeline writer if it’s still around
    subprocess.call(["pkill", "-f", SOX_PIPE_PAT],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def start_dial_tone():
    stop_playing()
    play_wav(os.path.join(SOUNDS, "dial_tone.wav"), loop=True)

def ringback_for(seconds=8):
    stop_playing()
    emit("ringback", {"sec": seconds})
    p = play_wav_for(os.path.join(SOUNDS, "ringback.wav"), seconds)
    if p: p.wait()

# ---- helpers: capture cleanup ----
def kill_stale_capture():
    """Ensure no previous capture pipeline is holding the device."""
    subprocess.call(["pkill", "-f", ARECORD_PAT],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.call(["pkill", "-f", SOX_PIPE_PAT],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# ---- single-shot "thinking" filler during LLM ----
filler_proc = None  # type: subprocess.Popen | None

def play_one_filler_once():
    """Play exactly one short filler clip (randomly chosen), non-blocking."""
    global filler_proc
    files = [
        os.path.join(SOUNDS, "filler_1.wav"),
        os.path.join(SOUNDS, "filler_2.wav"),
        os.path.join(SOUNDS, "filler_3.wav"),
    ]
    files = [f for f in files if os.path.exists(f)]
    if not files:
        return
    path = random.choice(files)
    # Play ~2.3s of the clip (keeps it snappy). Adjust if you want the full file.
    filler_proc = play_wav_for(path, 2.3)

def stop_filler():
    """Stop the filler if it's still playing (and ensure no aplay remains)."""
    global filler_proc
    if filler_proc and filler_proc.poll() is None:
        try:
            os.killpg(os.getpgid(filler_proc.pid), signal.SIGTERM)
        except Exception:
            pass
    filler_proc = None
    # Also ensure any stray aplay is gone
    stop_playing()


# ---- record + converse ----
def record_until_silence(out_wav):
    """Record mic; stop ~2s after trailing silence, with a hard cap so device always frees."""
    global recording_proc
    stop_playing()
    kill_stale_capture()

    # Hard-cap the arecord side; SoX will stop quicker if you stop speaking
    cmd = (
        f"{ARECORD_PAT} -f S16_LE -c1 -r16000 -d {MAX_RECORD_SEC} | "
        f"sox -t wav - -t wav {out_wav} silence 1 0.2 2% 1 2.0 2%"
    )
    recording_proc = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid)
    recording_proc.wait()
    recording_proc = None

def converse(persona, in_wav, out_wav):
    """POST to FastAPI /converse; save reply to out_wav. Fallback to click if it fails."""
    try:
        log(f"[NET] POST {SERVER}")
        play_one_filler_once()

        rc = subprocess.call([
            "curl","-s","-X","POST",
            "-F", f"persona={persona}",
            "-F", f"audio=@{in_wav};type=audio/wav",
            SERVER, "-o", out_wav
        ])

        stop_filler()

        if rc != 0 or not os.path.exists(out_wav) or os.path.getsize(out_wav) < 44:
            raise RuntimeError("server failed")
        return True
    except Exception as e:
        log(f"[NET] ERROR posting to server: {e}")
        stop_filler()
        subprocess.call(["cp", os.path.join(SOUNDS, "click.wav"), out_wav])
        emit("call_end", {"reason": "net_error"})
        return True

# ---- digit handling ----
def cancel_flush_timer():
    global flush_timer
    if flush_timer:
        try: flush_timer.cancel()
        except: pass
        flush_timer = None

def schedule_flush():
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

# ---- hook & dial callbacks ----
def on_hook_up():
    log("[HOOK] LIFTED")
    emit("phone_start", {})
    reset_call_state()
    kill_stale_capture()   # extra safety on lift
    start_dial_tone()

def on_hook_down():
    if not hung_up_stable():
        log("[HOOK] bounce ignored")
        return
    log("[HOOK] ON cradle")
    stop_filler()
    stop_playing()
    # kill entire record pipeline group if running
    global recording_proc
    if recording_proc:
        try:
            os.killpg(os.getpgid(recording_proc.pid), signal.SIGTERM)
        except Exception:
            pass
        recording_proc = None
    # also ensure no stragglers hold the device
    kill_stale_capture()
    emit("call_end", {"reason": "hangup"})
    reset_call_state()

def on_dial_pulse():
    global first_pulse_seen, pulse_count
    with state_lock:
        if not first_pulse_seen:
            first_pulse_seen = True
            stop_playing()
        pulse_count += 1
        schedule_flush()

def finalize_digit():
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

    if len(digits_str) == 3:
        code = digits_str
        reset_call_state()
        persona = PERSONAS.get(code, "einstein")
        log(f"[CALL] Connecting to {persona} ({code})…")

        # ringback → click → greeting
        ringback_for(8)
        p = play_wav(os.path.join(SOUNDS, "click.wav"));  p and p.wait()
        stop_playing()

        greet = os.path.join(SOUNDS, "greet_einstein.wav")
        if os.path.exists(greet):
            p = play_wav(greet);  p and p.wait()
        else:
            log("[GREET] greet_einstein.wav not found; skipping.")

        # record question
        qwav = os.path.expanduser("~/timephone/question.wav")
        rwav = os.path.expanduser("~/timephone/reply.wav")
        log("[REC] Ask your question… (auto-stops after silence or hard cap)")
        emit("record_start", {})
        t0 = time.monotonic()
        record_until_silence(qwav)
        dur = round(time.monotonic() - t0, 2)
        emit("record_done", {"sec": dur})

        if hook_on_cradle():
            log("[HOOK] Hung up during record; abort.")
            stop_filler()
            stop_playing()
            kill_stale_capture()
            emit("call_end", {"reason": "hangup_during_record"})
            reset_call_state()
            return

        # send to LLM & play reply
        log("[LLM] Sending to server…")
        ok = converse(persona, qwav, rwav)
        if ok and not hook_on_cradle():
            log("[PLAY] Reply…")
            p = play_wav(rwav);  p and p.wait()
        stop_filler()
        stop_playing()
        emit("call_end", {"reason": "ok"})

# ---- graceful shutdown ----
def _sigterm(*_):
    try:
        on_hook_down()
    finally:
        os._exit(0)

def main():
    signal.signal(signal.SIGTERM, _sigterm)
    signal.signal(signal.SIGINT, _sigterm)

    # cold-start hygiene
    stop_playing()
    kill_stale_capture()

    hook.when_pressed   = on_hook_up      # lifted
    hook.when_released  = on_hook_down    # on-cradle
    dial.when_released  = on_dial_pulse   # pulses

    log("TimePhone ready. Lift handset and dial a 3-digit code (e.g., 314). Ctrl+C to quit.")
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        on_hook_down()

if __name__ == "__main__":
    main()
