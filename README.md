# J.A.R.V.I.S.

A voice-controlled personal assistant for Windows, inspired by Tony Stark's JARVIS. Talk to it, and it talks back in a British male voice — and it can actually do things on your PC.

## Features

- **Voice conversations** — speech recognition + offline neural text-to-speech (Piper, British "Alan" voice)
- **JARVIS personality** — powered by a local LLM via Ollama (no cloud, no API keys)
- **Push-to-talk** — hold **Left Ctrl** and talk; no wake word needed
- **Real PC actions**:
  - Play random / genre music on Spotify, pause, skip tracks
  - Open apps, websites, Google search, YouTube
  - Set volume, mute, lock the PC, take screenshots, set timers
  - Live weather (free Open-Meteo API, no key)
  - Knows the current time, date and battery level
- **Streaming speech** — Jarvis starts answering while the model is still thinking
- Fully local brain, voice and speech recognition (Whisper) — only the weather needs internet. Google's free API is used as an automatic fallback for speech recognition.

## Requirements

- Windows 10/11
- Python 3.11+
- ~3 GB free disk space for the AI model + voice

## Setup

```powershell
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
powershell -ExecutionPolicy Bypass -File setup.ps1
Copy-Item config.example.json config.json
.\start_jarvis.bat
```

`setup.ps1` installs the Python dependencies, downloads the Piper voice and the Ollama runtime, and pulls the default AI model (`llama3.2:3b`).

If you prefer installing Ollama system-wide, download it from [ollama.com](https://ollama.com/download) — Jarvis detects it automatically.

## Usage

| Action | Effect |
| --- | --- |
| Hold **Left Ctrl** | Push-to-talk (say anything while held) |
| **F11** | Quit |
| Type in the window | Send a typed message |
| `/help` | Show all commands |
| `/mic <id>` | Choose a microphone |
| `/model <name>` | Switch AI model (auto-downloads) |

## Configuration

Edit `config.json` (created from `config.example.json`):

- `model` — Ollama model name (try `qwen2.5:7b` for a smarter brain, `llama3.2:1b` for speed)
- `city` — your city, so "what's the weather like?" works without naming one
- `mic_device` — microphone device index (use `/devices` in the app to list them)
- `stt_engine` — `auto` (local Whisper, recommended), `whisper`, or `google`; switch anytime with `/stt`
- `whisper_model` — Whisper model size (`tiny`, `base`, `small`; bigger = more accurate, slower)
- `cue_sound` — play a soft beep when recording starts
- `language`, `max_history` — assorted behavior

## Project structure

```
actions.py          Real PC actions (Spotify, apps, web, system, weather)
brain.py            Ollama client: JARVIS persona, streaming JSON action protocol
stt.py              Microphone capture with VAD (pre-roll, noise-adaptive) + Whisper/Google transcription
tts.py              Offline Piper TTS (British voice)
main.py             App: hotkeys, wake word / push-to-talk loops, speech queue
setup.ps1           One-time installer (deps, voice, Ollama, model)
```

## Notes

- Speech recognition uses the local Whisper model (downloaded on first run, ~150 MB) with Google's free API as automatic fallback. Everything except the weather works offline.
- The voice model, Whisper model and Ollama binary (~2 GB total) are downloaded by `setup.ps1` and excluded from git.
- Some actions (Spotify, weather) open external services in your default browser/apps.
