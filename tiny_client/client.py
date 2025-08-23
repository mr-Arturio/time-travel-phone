import io, requests, sounddevice as sd, soundfile as sf

API = "http://localhost:8000/converse"  # via your SSH tunnel
SR = 16000
SECONDS = 5

print("Recording... speak now!")
audio = sd.rec(int(SECONDS * SR), samplerate=SR, channels=1, dtype="float32")
sd.wait()

# Save recording to memory buffer as WAV
buf = io.BytesIO()
sf.write(buf, audio, SR, format="WAV")
buf.seek(0)

print("Sending to server...")
r = requests.post(
    API,
    data={"persona": "Isaac Newton"},
    files={"audio": ("ask.wav", buf.getvalue(), "audio/wav")},
    timeout=120
)

print("Transcript from Whisper:", r.headers.get("X-Transcript"))

print("Playing reply (stub silence for now)…")
data, sr = sf.read(io.BytesIO(r.content), dtype="float32")
sd.play(data, sr)
sd.wait()
print("Done.")
