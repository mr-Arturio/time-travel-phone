from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import StreamingResponse
import io, numpy as np, soundfile as sf

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/converse")
async def converse(persona: str = Form(...), audio: UploadFile = Form(...)):
    # --- read upload (we don't use it yet in the stub) ---
    _ = await audio.read()

    # --- make 2s of silence at 16kHz mono, 16-bit ---
    sr = 16000
    duration_s = 2.0
    y = np.zeros(int(sr * duration_s), dtype=np.float32)

    # --- write a real WAV into memory ---
    buf = io.BytesIO()
    sf.write(buf, y, sr, format="WAV", subtype="PCM_16")
    buf.seek(0)

    return StreamingResponse(buf, media_type="audio/wav")
