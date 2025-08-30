from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import StreamingResponse
import io, os, re, tempfile, subprocess, time, json, pathlib
import numpy as np, soundfile as sf
from faster_whisper import WhisperModel

app = FastAPI()

# ---------- Whisper configuration ----------
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "small.en")
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")  # "cpu" or "cuda"
WHISPER_COMPUTE = os.environ.get("WHISPER_COMPUTE", "int8" if WHISPER_DEVICE == "cpu" else "float16")

model = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE)

# ---------- Piper configuration ----------
# Prefer build path (your run.sh exports this); fallback to /root/piper/piper
PIPER_BIN = os.environ.get("PIPER_BIN", "/root/piper/build/piper")
PIPER_VOICE = os.environ.get("PIPER_VOICE", "/root/piper/voices/en_US-amy-low.onnx")
PIPER_JSON = os.environ.get("PIPER_JSON", f"{PIPER_VOICE}.json")

# ---------- Prosody helpers ----------
_SENT_SPLIT = re.compile(r'(?<=[\.\?\!])\s+')

def clean_and_punctuate(text: str) -> str:
    t = text.strip()
    if not t:
        return t
    # Capitalize first letter; ensure trailing punctuation.
    t = t[0].upper() + t[1:]
    if t[-1] not in ".?!":
        t += "."
    # Very light comma insertion for long runs (naive, but helps pacing)
    t = re.sub(r'(\w{6,})(\s+)(\w{6,})', r'\1,\2\3', t, count=1)
    return t

def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]

def resample_audio(y: np.ndarray, src_sr: int, dst_sr: int) -> np.ndarray:
    if src_sr == dst_sr:
        return y
    # Simple linear resample to avoid extra deps
    x_old = np.linspace(0, 1, num=len(y), endpoint=False, dtype=np.float64)
    n_new = int(round(len(y) * (dst_sr / float(src_sr))))
    x_new = np.linspace(0, 1, num=n_new, endpoint=False, dtype=np.float64)
    y_new = np.interp(x_new, x_old, y.astype(np.float64)).astype(np.float32)
    return y_new

def concat_wavs(buffers: list[bytes], target_sr: int | None = None, pause_ms: int = 120) -> bytes:
    """Concatenate multiple WAV bytes with short pauses; resample if needed."""
    waves = []
    srs = []
    for b in buffers:
        y, sr = sf.read(io.BytesIO(b), dtype="float32")
        waves.append(y)
        srs.append(sr)
    if not waves:
        # 1s of silence
        sr = target_sr or 16000
        blank = np.zeros(int(sr * 1.0), dtype=np.float32)
        out = io.BytesIO()
        sf.write(out, blank, sr, format="WAV", subtype="PCM_16")
        out.seek(0)
        return out.getvalue()

    # Pick a reference SR (first clip unless target_sr provided)
    ref_sr = target_sr or srs[0]
    # Resample clips if they differ
    waves = [resample_audio(y, srs[i], ref_sr) for i, y in enumerate(waves)]

    pause = np.zeros(int(ref_sr * (pause_ms/1000.0)), dtype=np.float32)
    seq = []
    for i, y in enumerate(waves):
        seq.append(y)
        if i != len(waves) - 1:
            seq.append(pause)
    ycat = np.concatenate(seq) if seq else pause
    out = io.BytesIO()
    sf.write(out, ycat, ref_sr, format="WAV", subtype="PCM_16")
    out.seek(0)
    return out.getvalue()

def piper_tts_once(text: str, model_path: str, json_path: str) -> bytes:
    """Run Piper for one short utterance and return WAV bytes."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        out_path = tmp.name
    try:
        # Prefer -m/-c/-f flags (work with build piper). Text via stdin (utf-8).
        cmd = [PIPER_BIN, "-m", model_path]
        if os.path.exists(json_path):
            cmd += ["-c", json_path]
        cmd += ["-f", out_path]
        subprocess.run(cmd, input=text.encode("utf-8"), check=True)
        with open(out_path, "rb") as f:
            data = f.read()
        return data
    finally:
        try:
            os.unlink(out_path)
        except Exception:
            pass

def piper_tts_multi(text: str, model_path: str, json_path: str, target_sr: int | None = None) -> bytes:
    text = clean_and_punctuate(text)
    parts = split_sentences(text)
    clips = []
    for s in parts if parts else [text]:
        try:
            clips.append(piper_tts_once(s, model_path, json_path))
        except Exception:
            # If one sentence fails, skip it; we'll still return what we have
            pass
    return concat_wavs(clips, target_sr=target_sr, pause_ms=120)

# ---------- Health ----------
@app.get("/health")
def health():
    return {
        "ok": True,
        "whisper_model": WHISPER_MODEL,
        "device": WHISPER_DEVICE,
        "piper_bin": PIPER_BIN,
        "piper_voice": PIPER_VOICE,
        "piper_json": PIPER_JSON,
        "piper_ok": os.path.exists(PIPER_BIN) and os.path.exists(PIPER_VOICE),
        "json_ok": os.path.exists(PIPER_JSON),
    }

# ---------- Main endpoint ----------
@app.post("/converse")
async def converse(persona: str = Form(...), audio: UploadFile = Form(...)):
    t_all0 = time.time()

    # 1) read upload
    wav_bytes = await audio.read()

    # 2) save to temp file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(wav_bytes)
        tmp_path = tmp.name

    # 3) transcribe (timed)
    t0 = time.time()
    segments, _info = model.transcribe(
        tmp_path,
        beam_size=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 300},
        language="en",
        initial_prompt="Casual, modern English conversation.",
    )
    transcript = "".join(s.text for s in segments).strip()
    t_stt = time.time() - t0

    # 4) cleanup temp audio
    try:
        os.unlink(tmp_path)
    except Exception:
        pass

    # 5) Generate reply text (LLM stub for now; swap in vLLM later)
    t1 = time.time()
    if transcript:
        reply_text = f"{persona} says: {clean_and_punctuate(transcript)}"
    else:
        reply_text = f"{persona} is listening."
    t_llm = time.time() - t1

    # 6) TTS via Piper (timed)
    t2 = time.time()
    try:
        audio_bytes = piper_tts_multi(reply_text, PIPER_VOICE, PIPER_JSON, target_sr=None)
        buf = io.BytesIO(audio_bytes)
    except Exception:
        # fallback to 1s silence
        sr = 16000
        y = np.zeros(int(sr * 1.0), dtype=np.float32)
        buf = io.BytesIO()
        sf.write(buf, y, sr, format="WAV", subtype="PCM_16")
        buf.seek(0)
    t_tts = time.time() - t2

    # 7) headers
    headers = {
        "X-Persona": persona,
        "X-Transcript": transcript[:1000] if transcript else "",
        "X-Whisper-Model": WHISPER_MODEL,
        "X-Device": WHISPER_DEVICE,
        "X-Timing-STT-ms": str(int(t_stt * 1000)),
        "X-Timing-LLM-ms": str(int(t_llm * 1000)),
        "X-Timing-TTS-ms": str(int(t_tts * 1000)),
        "X-Timing-Total-ms": str(int((time.time() - t_all0) * 1000)),
    }
    return StreamingResponse(buf, media_type="audio/wav", headers=headers)
