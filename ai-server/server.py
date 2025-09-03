from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse
import io, os, re, tempfile, subprocess, time, json, pathlib, shlex
from datetime import datetime, timezone
from collections import deque
import numpy as np, soundfile as sf
from faster_whisper import WhisperModel


# vLLM backend
try:
    import llm_backends
except Exception:
    llm_backends = None  # will gracefully fallback

app = FastAPI()

# ---------- Config / Env ----------
WHISPER_MODEL  = os.environ.get("WHISPER_MODEL", "small.en")
WHISPER_DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")         # "cpu" or "cuda"
WHISPER_COMPUTE= os.environ.get("WHISPER_COMPUTE", "int8" if WHISPER_DEVICE == "cpu" else "float16")

# Piper
PIPER_BIN   = os.environ.get("PIPER_BIN", "/root/piper/build/piper")
PIPER_VOICE = os.environ.get("PIPER_VOICE", "/root/piper/voices/en_US-amy-low.onnx")
PIPER_JSON  = os.environ.get("PIPER_JSON",  f"{PIPER_VOICE}.json")
PIPER_EXTRA_ARGS = os.environ.get("PIPER_EXTRA_ARGS", "").strip()  # pass-through to Piper CLI

# Personas
PERSONAS_PATH = os.environ.get("PERSONAS_PATH", "personas.json")

# ---- metrics ring buffer (unified) ----
METRICS_CAP = int(os.environ.get("METRICS_CAP", os.environ.get("METRICS_MAX", "50")))
METRICS: "deque[dict]" = deque(maxlen=METRICS_CAP)

# ---------- Load Whisper ----------
model = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE)

# ---------- Prosody helpers ----------
_SENT_SPLIT = re.compile(r'(?<=[\.\?\!])\s+')

def clean_and_punctuate(text: str) -> str:
    t = text.strip()
    if not t:
        return t
    t = t[0].upper() + t[1:]
    if t[-1] not in ".?!":
        t += "."
    t = re.sub(r'(\w{6,})(\s+)(\w{6,})', r'\1,\2\3', t, count=1)
    return t

def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]

def resample_audio(y: np.ndarray, src_sr: int, dst_sr: int) -> np.ndarray:
    if src_sr == dst_sr:
        return y
    x_old = np.linspace(0, 1, num=len(y), endpoint=False, dtype=np.float64)
    n_new = int(round(len(y) * (dst_sr / float(src_sr))))
    x_new = np.linspace(0, 1, num=n_new, endpoint=False, dtype=np.float64)
    y_new = np.interp(x_new, x_old, y.astype(np.float64)).astype(np.float32)
    return y_new

def concat_wavs(buffers: list[bytes], target_sr: int | None = None, pause_ms: int = 120) -> bytes:
    waves, srs = [], []
    for b in buffers:
        y, sr = sf.read(io.BytesIO(b), dtype="float32")
        waves.append(y); srs.append(sr)
    if not waves:
        sr = target_sr or 16000
        blank = np.zeros(int(sr * 1.0), dtype=np.float32)
        out = io.BytesIO()
        sf.write(out, blank, sr, format="WAV", subtype="PCM_16")
        out.seek(0)
        return out.getvalue()
    ref_sr = target_sr or srs[0]
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
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        out_path = tmp.name
    try:
        cmd = [PIPER_BIN, "-m", model_path]
        if os.path.exists(json_path):
            cmd += ["-c", json_path]
        if PIPER_EXTRA_ARGS:
            cmd += shlex.split(PIPER_EXTRA_ARGS)
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

def piper_tts_multi(text: str, model_path: str, json_path: str, target_sr: int | None = None, pause_ms: int = 120) -> bytes:
    text = clean_and_punctuate(text)
    parts = split_sentences(text)
    clips = []
    for s in parts if parts else [text]:
        try:
            clips.append(piper_tts_once(s, model_path, json_path))
        except Exception:
            pass
    return concat_wavs(clips, target_sr=target_sr, pause_ms=pause_ms)

# ---------- Personas ----------
def _load_personas() -> dict:
    try:
        with open(PERSONAS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

_PERSONAS = _load_personas()

def _persona_lookup(persona_key: str) -> dict:
    """
    persona_key may be a digit key like '1' or an 'id' field in any persona entry.
    Expected schema example:
    {
      "1": { "id": "einstein", "name": "Albert Einstein",
             "system": "You are Albert Einstein ...",
             "voice": "/root/piper/voices/en_US-amy-low.onnx" }
    }
    """
    if persona_key in _PERSONAS:
        return _PERSONAS[persona_key]
    # search by id
    for k, v in _PERSONAS.items():
        if isinstance(v, dict) and v.get("id") == persona_key:
            return v
    # default fallback
    return {
        "id": persona_key,
        "name": persona_key,
        "system": f"You are {persona_key}. Respond concisely and speak like the historical figure.",
        # no voice override by default
    }

# ---------- Metrics ----------
def _push_metric(m: dict) -> None:
    METRICS.append(m)

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

# ---------- Health ----------
@app.get("/health")
def health():
    llm_ok = False
    llm_ep = getattr(llm_backends, "ENDPOINT", None) if llm_backends else None
    llm_model = getattr(llm_backends, "MODEL", None) if llm_backends else None
    if llm_backends:
        try:
            llm_ok = llm_backends.health()
        except Exception:
            llm_ok = False
    return {
        "ok": True,
        "whisper_model": WHISPER_MODEL,
        "device": WHISPER_DEVICE,
        "piper_bin": PIPER_BIN,
        "piper_voice": PIPER_VOICE,
        "piper_json": PIPER_JSON,
        "piper_ok": os.path.exists(PIPER_BIN) and os.path.exists(PIPER_VOICE),
        "json_ok": os.path.exists(PIPER_JSON),
        "llm_endpoint": llm_ep,
        "llm_model": llm_model,
        "llm_ok": llm_ok,
        "personas_loaded": bool(_PERSONAS),
        "metrics_buffer": len(METRICS),
    }

# ---------- Mini dashboard ----------
@app.get("/metrics")
def metrics():
    items = list(METRICS)
    n = len(items)
    def avg(key: str) -> int:
        return int(sum(x["ms"].get(key, 0) for x in items) / n) if n else 0
    return JSONResponse({
        "n": n,
        "avg": {
            "stt":   avg("stt"),
            "llm":   avg("llm"),
            "tts":   avg("tts"),
            "total": avg("total"),
        },
        "items": items[::-1],  # newest first
    })

@app.get("/ui")
def ui():
    # tiny HTML with auto-refresh
    items = list(METRICS)[-50:][::-1]
    def esc(s: str) -> str:
        return (s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    rows = []
    for m in items:
        rows.append(
            f"<tr>"
            f"<td>{esc(m.get('ts'))}</td>"
            f"<td>{esc(m.get('persona'))}</td>"
            f"<td class='tx'>{esc(m.get('transcript',''))}</td>"
            f"<td class='tx'>{esc(m.get('reply_preview',''))}</td>"
            f"<td>{m.get('ms',{}).get('stt')}</td>"
            f"<td>{m.get('ms',{}).get('llm')}</td>"
            f"<td>{m.get('ms',{}).get('tts')}</td>"
            f"<td>{m.get('ms',{}).get('total')}</td>"
            f"</tr>"
        )
    html = f"""<!doctype html>
<html><head>
<meta charset="utf-8" />
<meta http-equiv="refresh" content="2" />
<title>Time-Travel Phone — Metrics</title>
<style>
body {{ font-family: system-ui, sans-serif; padding: 12px; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 6px 8px; vertical-align: top; }}
th {{ background: #f6f6f6; position: sticky; top: 0; }}
td.tx {{ max-width: 520px; white-space: pre-wrap; }}
small.mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; color: #555; }}
</style>
</head>
<body>
<h2>Time-Travel Phone — Metrics</h2>
<div><small class="mono">/metrics returns JSON; this page auto-refreshes every 2s</small></div>
<table>
<thead>
<tr>
  <th>Time (UTC)</th><th>Persona</th><th>Transcript</th><th>Reply (preview)</th>
  <th>STT ms</th><th>LLM ms</th><th>TTS ms</th><th>Total ms</th>
</tr>
</thead>
<tbody>
{''.join(rows)}
</tbody>
</table>
</body></html>
"""
    return HTMLResponse(html)

# ---------- Main endpoint ----------
@app.post("/converse")
async def converse(persona: str = Form(...), audio: UploadFile = Form(...)):
    t_all0 = time.time()
    persona_info = _persona_lookup(persona)
    system_prompt = persona_info.get("system") or f"You are {persona_info.get('name', persona)}. Be concise."
    # Allow per-persona voice override
   voice_path = persona_info.get("voice", PIPER_VOICE)              # expects .onnx
  voice_json = persona_info.get("voice_json", f"{voice_path}.json") # optional explicit override
  # safety: if user mistakenly set .json in 'voice', try to recover
  if voice_path.endswith(".json"):
    guess = voice_path[:-5]  # strip .json
    if os.path.exists(guess):
        voice_path = guess


    # 1) read upload
    wav_bytes = await audio.read()

    # 2) save temp
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(wav_bytes)
        tmp_path = tmp.name

    # 3) transcribe
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

    # cleanup temp
    try: os.unlink(tmp_path)
    except Exception: pass

    # 4) LLM (vLLM if up, else fallback stub)
    t1 = time.time()
    used_llm = False
    reply_text = ""
    if transcript:
        if llm_backends and llm_backends.health():
            try:
                reply_text = llm_backends.chat(system_prompt, transcript)
                used_llm = True
            except Exception:
                used_llm = False
        if not used_llm:
            reply_text = f"{persona_info.get('name', persona)} says: {clean_and_punctuate(transcript)}"
    else:
        reply_text = f"{persona_info.get('name', persona)} is listening."
    t_llm = time.time() - t1

    # 5) TTS
    t2 = time.time()
    try:
        audio_bytes = piper_tts_multi(reply_text, voice_path, voice_json, target_sr=None, pause_ms=120)
        buf = io.BytesIO(audio_bytes)
    except Exception:
        sr = 16000
        y = np.zeros(int(sr * 1.0), dtype=np.float32)
        buf = io.BytesIO()
        sf.write(buf, y, sr, format="WAV", subtype="PCM_16")
        buf.seek(0)
    t_tts = time.time() - t2

    # 6) metrics
    METRICS.append({
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "persona": persona_info.get("id", persona),
        "name": persona_info.get("name", persona),
        "transcript": transcript,
        "reply_preview": reply_text[:500],
        "ms": {
            "stt":   int(t_stt * 1000),
            "llm":   int(t_llm * 1000),
            "tts":   int(t_tts * 1000),
            "total": int((time.time() - t_all0) * 1000),
        },
        "llm_used": used_llm,
    })

    # 7) headers
    headers = {
        "X-Persona": persona_info.get("id", persona),
        "X-Transcript": transcript[:1000] if transcript else "",
        "X-Whisper-Model": WHISPER_MODEL,
        "X-Device": WHISPER_DEVICE,
        "X-LLM-Endpoint": getattr(llm_backends, "ENDPOINT", "") if llm_backends else "",
        "X-LLM-Model": getattr(llm_backends, "MODEL", "") if llm_backends else "",
        "X-LLM-Used": "1" if used_llm else "0",
        "X-Timing-STT-ms": str(int(t_stt * 1000)),
        "X-Timing-LLM-ms": str(int(t_llm * 1000)),
        "X-Timing-TTS-ms": str(int(t_tts * 1000)),
        "X-Timing-Total-ms": str(int((time.time() - t_all0) * 1000)),
    }
    return StreamingResponse(buf, media_type="audio/wav", headers=headers)
