from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import StreamingResponse
import io, os, tempfile, subprocess
import numpy as np, soundfile as sf
from faster_whisper import WhisperModel

app = FastAPI()

# ---------- Whisper configuration ----------
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "small.en")
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")  # "cpu" or "cuda"
WHISPER_COMPUTE = os.environ.get(
    "WHISPER_COMPUTE",
    "int8" if WHISPER_DEVICE == "cpu" else "float16"
)

model = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE)

# ---------- Piper configuration ----------
PIPER_BIN = os.environ.get("PIPER_BIN", "/root/piper/piper")
PIPER_VOICE = os.environ.get("PIPER_VOICE", "/root/piper/voices/en_US-amy-low.onnx")

@app.get("/health")
def health():
    return {
        "ok": True,
        "whisper_model": WHISPER_MODEL,
        "device": WHISPER_DEVICE,
        "piper_bin": PIPER_BIN,
        "piper_voice": PIPER_VOICE,
        "piper_ok": os.path.exists(PIPER_BIN) and os.path.exists(PIPER_VOICE)
    }

@app.post("/converse")
async def converse(persona: str = Form(...), audio: UploadFile = Form(...)):
    # 1) read upload
    wav_bytes = await audio.read()

    # 2) save to temp file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(wav_bytes)
        tmp_path = tmp.name

    # 3) transcribe
    segments, _info = model.transcribe(
        tmp_path,
        beam_size=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 300},
        language="en",
        initial_prompt="Casual, modern English conversation.",
    )
    transcript = "".join(s.text for s in segments).strip()

    # 4) cleanup temp audio
    try:
        os.unlink(tmp_path)
    except Exception:
        pass

    # 5) Generate reply text (very simple for now)
    reply_text = f"{persona} says: I heard you say {transcript}" if transcript else f"{persona} is listening."

    # 6) Use Piper to synthesize reply
    out_wav = "/tmp/reply.wav"
    try:
        cmd = [PIPER_BIN, "--model", PIPER_VOICE, "--output_file", out_wav]
        subprocess.run(cmd, input=reply_text.encode("utf-8"), check=True)

        with open(out_wav, "rb") as f:
            audio_bytes = f.read()
        buf = io.BytesIO(audio_bytes)
    except Exception as e:
        # fallback to silence if Piper fails
        sr = 16000
        y = np.zeros(int(sr * 1.0), dtype=np.float32)
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
