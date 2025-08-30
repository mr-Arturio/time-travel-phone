## Inspiration
Imagine you’re an 8th-grader in history class. Your teacher is talking about **Julius Caesar** or **Abraham Lincoln** and then asks: _“If you could call them right now, what would you ask?”_
They pull out a **rotary phone** - a real one. _“Pick one question. Dial the number. Listen.”_
You spin the dial, hold the handset to your ear, and hear a reply in the figure’s own voice and style. The contrast of vintage hardware and living answers turns a normal lesson into a core memory.

## What it does
Pick up an old rotary phone, dial a number, and ask a question. On the other end, a historical figure answers — in their voice, style, and worldview. This project fuses retro hardware with open-source AI to create a playful, educational “time line” you can literally dial.

_I got Einstein on a speed dial... Do you?_

- Rotary dial selects a persona (e.g., 5565 → Newton, 0314 → Einstein, 1865 → Lincoln).
- The Raspberry Pi hidden inside the phone captures the handset audio and posts it to a local AI server.
- Whisper transcribes the question.
-  A persona-aware prompt and RAG context go to a gpt-oss model served by vLLM.
- Piper TTS returns a reply in an era-appropriate, inspired voice, which plays through the handset speaker.

## How we built it
### Hardware
- Refurbished rotary phone as the enclosure; Raspberry Pi mounted inside the shell.
-  AKG earbuds as the handset’s speaker + microphone, connected via a USB audio dongle to the Pi.
- Rotary dial pulses read on GPIO with debouncing; hook switch detection wired to GPIO to auto start/stop recording.

### Software
- FastAPI server providing /health and /converse endpoints.
- Speech-to-text via faster-whisper (Whisper medium.en/large-v3 depending on hardware).
- Persona reply via gpt-oss-20B served locally using vLLM (OpenAI-compatible). System prompts constrain era knowledge, tone, and length; optional retrieval adds citations from curated corpora.
- Text-to-speech via Piper with per-persona presets (rate, pitch, energy).
- Client on the Pi records 16 kHz mono WAV, posts it to /converse, and plays back the returned WAV

## Challenges I ran into

- Integrating the Raspberry Pi neatly inside a vintage phone shell while maintaining serviceability and airflow.
- Reliable hook-switch detection to auto start/stop recording and reset state between calls.
- Debouncing and digit accuracy on the rotary dial pulse train under noisy electrical conditions.
- Ensuring every reply is a valid WAV (sample rate, channels, PCM subtype) so playback never fails mid-demo.
- Latency tradeoffs between Whisper accuracy, LLM size, and TTS quality; budgeting response length and temperature.
- Cross-platform audio quirks between Linux on the Pi and the server environment.

## Accomplishments that we're proud of

- A complete, reliable end-to-end experience: pick up, dial, speak, and hear a historically grounded answer in seconds.
- Fully local stack with gpt-oss-20B via vLLM, Whisper STT, and Piper TTS—no external AI APIs.
- Clean hardware integration: Pi, audio, dial, and hook switch all working inside the restored phone.
- Persona prompts and retrieval that keep answers concise, in-character, and bounded by the figure’s lifetime knowledge.
- Demo stability: health checks, environment toggles, and fallbacks so the phone always “says something.

## What we learned
- **Practical phone archaeology**: classic rotary phones are line-powered; modernizing them safely means rethinking audio (use hidden USB mic/speaker) and controls (GPIO for dial + hook).
- **Linux audio pipelines**: strict WAV formatting (16 kHz, mono, PCM_16) is non-negotiable for reliable playback across tools/drivers.
- **Perceived vs. raw latency**: short, pre-recorded “thinking” fillers + tight token budgets, low temperature, and brief TTS keep the call feeling instant.
- **Persona design is a craft**: style cards, era boundaries, retrieval with citations, and concise tone improve both faithfulness and charm.
- **Rented GPU on RunPod.io**: learned to choose practical GPUs (use 20B + 4-bit on 24 GB cards), understand spot vs on-demand, open an SSH tunnel, spin up a FastAPI + Whisper stack, expose /health, and add CPU/GPU fallbacks via env vars. Also got the hang of pinning model versions, watching VRAM, and shutting pods down to control costs

## What's next for Time Travel Phone
- Audio polish: add subtle line tones, ringback, and era-appropriate line static to heighten the illusion.
- Filler responses: short, pre-recorded persona phrases that play instantly while the model generates the main answer.
- More personas: Marie Curie, Ada Lovelace, Nikola Tesla, Frederick Douglass, Hypatia, and others, each with a style card and curated corpus.
- Kiosk mode: timed sessions, volume limiter, and on-device signage for museums and classrooms.
- Accessibility: captions on a small companion display and a handset volume rocker.
- Packaging: a turnkey image (Docker Compose + preloaded weights) for simple school/museum installs.
- Full conversations (multi-turn): True back-and-forth dialogue after advanced model training:
   - Multi-turn memory (short-term context window + persona-consistent recall).
   - Conversation manager to track topics, follow-ups, and clarifying questions.
   - RAG across turns so answers build on previous context with citations.
   - Natural turn-taking (VAD/barge-in) and streaming TTS for snappier, interruptible replies.