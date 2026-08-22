# J.A.R.V.I.S.

A voice-controlled personal assistant for Windows, inspired by Tony Stark's JARVIS. Talk to it, and it talks back in a British male voice — and it can actually do things on your PC.

## Features

- **Voice conversations** — speech recognition + offline neural text-to-speech (Piper, British "Alan" voice)
- **JARVIS personality** — powered by a local LLM via Ollama (no cloud, no API keys)
- **Push-to-talk** — hold **Left Ctrl** and talk; no wake word needed
- **Real PC actions**:
  - Play random / genre music on Spotify, pause, skip tracks
  - Open any installed app by name (Spotify, Discord, VS Code, etc.)
  - Open websites, Google search, YouTube
  - Set volume, mute/deafen, lock the PC, take screenshots, set timers
  - Live weather (free Open-Meteo API, no key)
  - Currency conversion (live rates, any currency)
  - Steam game management — launch installed games, auto-download uninstalled ones
  - Knows the current time, date and battery level
- **Focus mode** — pin the AI model in GPU memory for near-instant responses
- **Streaming speech** — Jarvis starts answering while the model is still thinking
- Fully local brain, voice and speech recognition (Whisper) — only the weather, search and currency rates need internet

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

## Usage

| Action | Effect |
| --- | --- |
| Hold **Left Ctrl** | Push-to-talk (say anything while held) |
| **F11** | Quit |
| Type in the window | Send a typed message |
| `/help` | Show all commands |
| `/mic <id>` | Choose a microphone |
| `/model <name>` | Switch AI model (auto-downloads) |
| `/devices` | List available microphone devices |
| `/stt <engine>` | Switch speech engine: `auto`, `whisper`, or `google` |

## Voice Commands

Jarvis understands natural speech. Here are some examples:

**General**
- "Hey Jarvis, what time is it?"
- "Tell me a joke"
- "What's the weather in Paris?"

**Music**
- "Play some music" / "Play random music"
- "Pause" / "Resume" / "Skip"

**Apps & Websites**
- "Open Spotify" / "Open Visual Studio Code"
- "Search Google for the best restaurants"
- "Open youtube.com"

**System**
- "Set volume to 50"
- "Mute" / "Unmute" / "Deafen" / "Undeafen"
- "Lock my computer"
- "Take a screenshot"
- "Set a 10 minute timer"

**Steam Games**
- "Play Overwatch" — launches the game (starts download if not installed)
- "I want to play Apex Legends" — auto-downloads if not installed
- "Launch Rust" — launches installed games
- Works with game names, abbreviations ("cod" for Call of Duty), and partial matches

**Currency**
- "How much is 100 dollars in Tunisian dinars?"
- "Convert 50 euros to USD"

**Focus Mode**
- "Jarvis, focus mode on" — pins the model in GPU memory for instant answers
- "Jarvis, focus mode off" — returns to normal mode

## Configuration

Edit `config.json` (created from `config.example.json`):

- `model` — Ollama model name (try `qwen2.5:7b` for a smarter brain, `llama3.2:1b` for speed)
- `city` — your city, so "what's the weather like?" works without naming one
- `mic_device` — microphone device index (use `/devices` in the app to list them)
- `stt_engine` — `auto` (local Whisper, recommended), `whisper`, or `google`
- `whisper_model` — Whisper model size (`tiny`, `base`, `small`; bigger = more accurate, slower)

## Project Structure

```
actions.py          Real PC actions (Spotify, apps, web, system, weather, Steam)
brain.py            Ollama client: JARVIS persona, streaming JSON action protocol
stt.py              Microphone capture with VAD + Whisper/Google transcription
tts.py              Offline Piper TTS (British voice)
main.py             App: hotkeys, push-to-talk loop, speech queue, focus mode
steam.py            Steam game discovery, launch, install via steam:// protocol
apps.py             Start Menu app discovery for launching any installed program
media.py            Spotify playback control
project.py          Project setup wizard
setup.ps1           One-time installer (deps, voice, Ollama, model)
config.json         Runtime configuration (not committed)
```

## Notes

- Speech recognition uses the local Whisper model with Google's free API as automatic fallback. Everything except the weather, search and currency works offline.
- Steam game management auto-discovers your library from `libraryfolders.vdf` and all `appmanifest_*.acf` files. Games not found locally are searched on the Steam Store.
- Focus mode uses `keep_alive: -1` to prevent Ollama from unloading the model. The system prompt was trimmed to ~400 tokens for fast prompt evaluation.
- Some actions (Spotify, weather, search) open external services in your default browser/apps.
