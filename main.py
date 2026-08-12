import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from queue import Queue

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from pynput import keyboard

import actions
from brain import JarvisBrain
from stt import SpeechToText
from tts import JarvisVoice

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
OLLAMA_EXE = os.path.join(BASE_DIR, "ollama", "ollama.exe")
OLLAMA_INSTALL_EXE = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe")
OLLAMA_PATHS = [OLLAMA_EXE, OLLAMA_INSTALL_EXE, "ollama"]

DEFAULT_CONFIG = {
    "model": "llama3.2:3b",
    "voice": "voices/en_GB-alan-medium.onnx",
    "ollama_url": "http://localhost:11434",
    "language": "en-US",
    "wake_word_enabled": True,
    "wake_words": ["jarvis", "hey jarvis", "ok jarvis"],
    "max_history": 20,
    "mic_device": None,
    "city": "",
}

BANNER = r"""
  ╔══════════════════════════════════════════════════╗
  ║   J.A.R.V.I.S.  -  Just A Rather Very Intelligent║
  ║   System  -  at your service, sir.               ║
  ╚══════════════════════════════════════════════════╝
"""

HELP = """COMMANDS
  Hold LEFT CTRL      : push to talk (say anything, no wake word needed)
  F12                 : toggle wake word listening on/off
  F11                 : quit Jarvis
  Type in this window : send a typed message instead
  /devices            : list microphone devices
  /mic <id>           : choose a microphone
  /model <name>       : change the AI model
  /wake               : toggle wake word mode
  /help               : show this help
  /quit               : quit Jarvis"""


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    return cfg


def save_config(cfg: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def ensure_ollama(cfg: dict) -> None:
    brain = JarvisBrain(cfg["ollama_url"], cfg["model"])
    if brain.ping():
        return
    print("[boot] Ollama not running - starting it...")
    for path in OLLAMA_PATHS:
        exe = shutil.which(path) if not os.path.isfile(path) else path
        if exe:
            subprocess.Popen([exe, "serve"], creationflags=subprocess.CREATE_NO_WINDOW)
            for _ in range(30):
                time.sleep(1)
                if brain.ping():
                    break
            else:
                continue
            break
    else:
        print("[boot] ERROR: Ollama not found. Install it from https://ollama.com/download or run setup.ps1")
        sys.exit(1)
    print("[boot] Ollama ready.")


class SpeechManager:
    def __init__(self, voice):
        self.voice = voice
        self.queue = Queue()
        self.speaking = False
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self) -> None:
        while True:
            item = self.queue.get()
            self.speaking = True
            try:
                self.voice.speak(item)
            finally:
                self.speaking = False
                self.queue.task_done()

    def say(self, text: str) -> None:
        if text:
            self.queue.put(text)

    def say_sync(self, text: str) -> None:
        self.say(text)
        self.queue.join()

    def flush(self) -> None:
        self.queue.join()


class JarvisApp:
    def __init__(self):
        self.cfg = load_config()
        ensure_ollama(self.cfg)
        self.brain = JarvisBrain(self.cfg["ollama_url"], self.cfg["model"], self.cfg["max_history"], self.cfg.get("city", ""))
        actions.CITY = self.cfg.get("city", "")
        if not self.brain.ping():
            print("[boot] ERROR: cannot reach Ollama API at", self.cfg["ollama_url"])
            sys.exit(1)
        print(f"[boot] ensuring model '{self.cfg['model']}'...")
        self.brain.ensure_model()
        voice_path = os.path.join(BASE_DIR, self.cfg["voice"]) if not os.path.isabs(self.cfg["voice"]) else self.cfg["voice"]
        print("[boot] loading voice...")
        self.voice = JarvisVoice(voice_path)
        self.speech = SpeechManager(self.voice)
        self.stt = SpeechToText(self.cfg["language"], self.cfg["mic_device"])
        self.ctrl_held = False
        self.wake_enabled = self.cfg["wake_word_enabled"]
        self.quit_event = threading.Event()
        self.processing = threading.Lock()
        self._partial_reply = ""
        print(BANNER)
        print(HELP)
        self._status()
        threading.Thread(target=self._prewarm, daemon=True).start()

    def _prewarm(self) -> None:
        try:
            for _ in self.brain.ask_stream("Reply with the single word: Ready."):
                pass
        except Exception:
            pass

    def _status(self) -> None:
        mode = "WAKE WORD" if self.wake_enabled else "PUSH-TO-TALK ONLY"
        print(f"\n  [{mode}]  Say \"Jarvis...\" then your command.  (F12 to toggle, F11 to quit)")
        print("  " + "-" * 56)

    def on_press(self, key) -> None:
        if key == keyboard.Key.ctrl_l:
            self.ctrl_held = True
        elif key == keyboard.Key.f12:
            self.wake_enabled = not self.wake_enabled
            print(f"\n  [system] Wake word mode {'ON' if self.wake_enabled else 'OFF'}")
        elif key == keyboard.Key.f11:
            print("\n  [system] Shutting down. Goodbye, sir.")
            self.quit_event.set()

    def on_release(self, key) -> None:
        if key == keyboard.Key.ctrl_l:
            self.ctrl_held = False

    def speak(self, text: str, sync: bool = False) -> None:
        if text:
            if sync:
                self.speech.say_sync(text)
            else:
                self.speech.say(text)

    def _feed_reply(self, chunk: str) -> None:
        self._partial_reply += chunk
        while True:
            m = re.search(r"(?<=[.!?])\s+", self._partial_reply)
            if not m:
                break
            sent = self._partial_reply[:m.start()].strip()
            self._partial_reply = self._partial_reply[m.start():]
            if sent:
                self.speech.say(sent)

    def _flush_reply(self) -> None:
        if self._partial_reply.strip():
            self.speech.say(self._partial_reply.strip())
        self._partial_reply = ""

    def process(self, text: str) -> None:
        text = text.strip()
        if not text:
            return
        if not text.startswith("/"):
            print(f"\n  YOU    > {text}")
        with self.processing:
            reply = ""
            action = None
            try:
                for event in self.brain.ask_stream(text):
                    if event["type"] == "text":
                        self._feed_reply(event["text"])
                    elif event["type"] == "done":
                        reply = event["reply"]
                        action = event["action"]
            except Exception as e:
                self._flush_reply()
                self.speech.say_sync("I'm afraid my systems are struggling right now, sir.")
                print(f"  [error] {e}")
                return
            self._flush_reply()
            calls = []
            results = []
            if action:
                calls.append({"name": action["name"], "args": action.get("args") or {}})
                results.append(actions.run_action(action["name"], action.get("args") or {}))
            self.brain.commit_turn(text, reply, calls, results)
            if reply.strip():
                print(f"\n  JARVIS > {reply.strip()}")
            if results:
                self.speech.flush()
                for res in results:
                    print(f"\n  JARVIS > {res}")
                    self.speech.say_sync(res)

    def handle_command(self, line: str) -> bool:
        cmd = line.strip().lower()
        if cmd in ("/quit", "/exit", "quit", "exit", "goodbye"):
            self.quit_event.set()
            return False
        if cmd == "/help":
            print(HELP)
        elif cmd == "/wake":
            self.wake_enabled = not self.wake_enabled
            print(f"  [system] Wake word mode {'ON' if self.wake_enabled else 'OFF'}")
        elif cmd == "/devices":
            print("  Microphone devices:")
            print(self.stt.list_devices())
        elif cmd.startswith("/mic "):
            try:
                dev = int(cmd[5:])
                self.stt.device = dev
                self.cfg["mic_device"] = dev
                save_config(self.cfg)
                print(f"  [system] Mic set to device {dev}")
            except ValueError:
                print("  [system] Usage: /mic <id>")
        elif cmd.startswith("/model "):
            name = cmd[7:].strip()
            self.cfg["model"] = name
            save_config(self.cfg)
            self.brain.model = name
            print(f"  [system] Model set to {name}. Ensuring it's available...")
            try:
                self.brain.ensure_model()
            except Exception as e:
                print(f"  [error] {e}")
        else:
            self.process(line)
        return True

    def stdin_loop(self) -> None:
        while not self.quit_event.is_set():
            try:
                line = input()
            except EOFError:
                time.sleep(0.5)
                continue
            if not self.handle_command(line):
                break

    def listen_loop(self) -> None:
        while not self.quit_event.is_set():
            if self.speech.speaking:
                time.sleep(0.1)
                continue
            if self.ctrl_held:
                audio = self.stt.record_while(lambda: self.ctrl_held and not self.quit_event.is_set())
                if audio is not None:
                    try:
                        text = self.stt.transcribe(audio)
                    except RuntimeError as e:
                        print(f"  [error] {e}")
                        text = None
                    if text:
                        self.process(text)
                    else:
                        print("  [system] Didn't catch that, sir.")
                continue
            if self.wake_enabled:
                try:
                    audio = self.stt.record_utterance()
                except Exception:
                    if self.quit_event.is_set():
                        break
                    time.sleep(0.2)
                    continue
                if audio is None:
                    continue
                try:
                    text = self.stt.transcribe(audio)
                except RuntimeError as e:
                    print(f"  [error] {e}")
                    continue
                if not text:
                    continue
                lower = text.lower().strip()
                words = lower.split()
                if not words:
                    continue
                first = words[0].strip(".,!? ")
                if first not in self.cfg["wake_words"] and lower not in self.cfg["wake_words"]:
                    continue
                command = lower
                for w in self.cfg["wake_words"]:
                    if lower.startswith(w):
                        command = lower[len(w):].strip(" ,.!?")
                        break
                if not command:
                    self.speak("Yes, sir?", sync=True)
                    continue
                print(f"\n  YOU    > {text}")
                self.process(text)
            else:
                time.sleep(0.1)

    def run(self) -> None:
        listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        listener.start()
        stdin_thread = threading.Thread(target=self.stdin_loop, daemon=True)
        stdin_thread.start()
        listen_thread = threading.Thread(target=self.listen_loop, daemon=True)
        listen_thread.start()
        while not self.quit_event.wait(0.2):
            pass


if __name__ == "__main__":
    JarvisApp().run()
