import sounddevice as sd
import soundfile as sf

SR = 16000
SECONDS = 3

print("🎤 Recording 3 seconds...")
audio = sd.rec(int(SECONDS * SR), samplerate=SR, channels=1, dtype="float32")
sd.wait()

sf.write("sample.wav", audio, SR, format="WAV", subtype="PCM_16")
print("✅ Saved sample.wav")
