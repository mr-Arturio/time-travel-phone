import io, requests, sounddevice as sd, soundfile as sf

API = "http://localhost:8000/converse"
SR = 16000
SECONDS = 5

print("Recording... speak now!")
audio = sd.rec(int(SECONDS * SR), samplerate=SR, channels=1, dtype="float32")
sd.wait()

# Save local copy
sf.write("last_input.wav", audio, SR, format="WAV", subtype="PCM_16")
print("✅ Saved your input to last_input.wav")

# Send to server
buf = io.BytesIO()
sf.write(buf, audio, SR, format="WAV")
buf.seek(0)

print("Sending to server...")
r = requests.post(
    API,
    data={"persona": "Albert Einstein"},
    files={"audio": ("ask.wav", buf.getvalue(), "audio/wav")},
    timeout=120
)

print("Transcript from Whisper:", r.headers.get("X-Transcript"))

print("Playing reply…")
data, sr = sf.read(io.BytesIO(r.content), dtype="float32")
sf.write("reply.wav", data, sr, format="WAV", subtype="PCM_16")  # save reply too
sd.play(data, sr)
sd.wait()
print("✅ Reply also saved to reply.wav")
