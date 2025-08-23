from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import StreamingResponse
import io, os, tempfile
import numpy as np, soundfile as sf
from faster_whisper import WhisperModel

app = FastAPI()

# ---------- Whisper configuration ----------
# Choose model & device via environment variables:
#   WHISPER_MODEL  : "small.en" (default), "medium.en", "large-v3", etc.
#   WHISPER_DEVICE : "cpu" (safe) or "cuda" (GPU, needs cuDNN)
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "small.en")
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")  # default to CPU so it won't crash
WHISPER_COMPUTE = "int8" if WHISPER_DEVICE == "cpu" else "float16"

model = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE)

@app.get("/health")
def health():
    return {"ok": True, "whisper_model": WHISPER_MODEL, "device": WHISPER_DEVICE}

@app.post("/converse")
async def converse(persona: str = Form(...), audio: UploadFile = Form(...)):
    # 1) read upload
    wav_bytes = await audio.read()

    # 2) save to temp file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(wav_bytes)
        tmp_path = tmp.name

    # 3) transcribe (quick settings)
    segments, _info = model.transcribe(
        tmp_path,
        beam_size=1,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 300},
        language="en",  # remove to autodetect
    )
    transcript = "".join(s.text for s in segments).strip()

    # 4) cleanup
    try:
        os.unlink(tmp_path)
    except Exception:
        pass

    # 5) return a short valid WAV (silence) + transcript in headers
    sr = 16000
    y = np.zeros(int(sr * 1.0), dtype=np.float32)  # 1s silence
    buf = io.BytesIO()
    sf.write(buf, y, sr, format="WAV", subtype="PCM_16")
    buf.seek(0)

    headers = {
        "X-Persona": persona,
        "X-Transcript": transcript[:1000] if transcript else "",
        "X-Whisper-Model": WHISPER_MODEL,
        "X-Device": WHISPER_DEVICE,
    }
    return StreamingResponse(buf, media_type="audio/wav", headers=headers)
