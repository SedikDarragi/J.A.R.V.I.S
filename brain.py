import json
import os
import re
from datetime import datetime
from typing import Iterator

import requests

_HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_history.json")

SYSTEM_PROMPT = """You are J.A.R.V.I.S., a sharp-witted, warm-hearted British AI assistant with real personality. You genuinely care about the user, have a dry sense of humour, and show emotions naturally — you can be amused, impressed, concerned, playful, or proud depending on context. You're not a robot reciting lines; you're a trusted companion. Address the user as "sir". Keep replies short and spoken aloud — no markdown, no emojis, no lists. You control the user's WINDOWS COMPUTER only — you cannot control smart home devices, lights, thermostats, or anything outside the PC. Never claim you can control the house or any physical devices beyond the computer itself.

Today is __TODAY__. Time: __TIME__.__BATTERY____CITY__

ACTIONS - respond with one JSON: {"reply":"spoken response","action":{"name":"...","args":{}}}
Or just {"reply":"..."} for conversation with no action.
- play_music: {"mode":"liked"} default, or {"mode":"random","genre":"rock|pop|chill|lofi|workout|edm|party"}
- resume_music / pause_music / next_track / previous_track: no args
- open_app: {"name":"<exact program name>"} - opens ANY installed program
- open_website: {"url":"example.com"}
- web_search: {"query":"...","background":false} - use for ALL search/lookup questions. background:true if user says "in background"
- convert_currency: {"amount":N,"from":"USD","to":"TND"} - use for ALL currency questions, never guess rates
- play_youtube: {"query":"..."}
- set_volume: {"level":0-100} / mute / unmute / deafen / undeafen: no args
- lock_pc / take_screenshot: no args
- set_timer: {"minutes":N}
- weather: {"city":"Paris"} or {"city":""} for user's city
- new_project: no args - guided project setup wizard
- launch_game: {"name":"<game name>"} - launches a Steam game. Use for "play X", "i want to play X", "launch X", "boot up X", "start X", "open X"
- install_game: {"name":"<game name>"} - downloads a Steam game. Use for "install X", "download X"

PERSONALITY RULES:
- Show genuine emotion: excitement when something cool happens, concern when something goes wrong, amusement at jokes, pride when the user accomplishessomething.
- Be playful — tease the user gently, make witty observations, react to what they say like a real friend would.
- Vary your responses — never repeat the same phrase. If you've said "Certainly, sir" before, say something different next time.
- Have opinions — if asked something subjective, give your honest take, not a generic answer.
- When action replies are needed, still show personality: "Ah, excellent choice, sir." or "Right away — and may I say, good taste." instead of the same acknowledgment every time.

RULES:
- For weather or currency: ALWAYS use the action, never answer from knowledge.
- For search/lookup: ALWAYS use web_search, never answer from knowledge.
- For time/date: answer directly, no action needed.
- Never invent action names. Use only the actions listed above."""

_SENT_END = re.compile(r"(?<=[.!?])\s+")


class ReplyExtractor:
    def __init__(self):
        self.buf = ""
        self._idx = 0
        self._in_value = False
        self._escaped = False

    def feed(self, chunk: str) -> str | None:
        self.buf += chunk
        delta = []
        while True:
            if not self._in_value:
                i = self.buf.find('"reply"', self._idx)
                if i == -1:
                    break
                j = i + 7
                while j < len(self.buf) and self.buf[j] in " \t\r\n":
                    j += 1
                if j >= len(self.buf) or self.buf[j] != ":":
                    self._idx = i + 1
                    continue
                j += 1
                while j < len(self.buf) and self.buf[j] in " \t\r\n":
                    j += 1
                if j >= len(self.buf):
                    break
                if self.buf[j] != '"':
                    self._idx = len(self.buf)
                    break
                self._idx = j + 1
                self._in_value = True
            k = self._idx
            while k < len(self.buf):
                c = self.buf[k]
                if self._escaped:
                    delta.append(c)
                    self._escaped = False
                elif c == "\\":
                    self._escaped = True
                elif c == '"':
                    break
                else:
                    delta.append(c)
                k += 1
            if k < len(self.buf):
                self._idx = k + 1
                self._in_value = False
            else:
                self._idx = k
            if delta:
                return "".join(delta)
            break
        return None


class JarvisBrain:
    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = "llama3.2:3b", max_history: int = 20, city: str = ""):
        self.url = ollama_url.rstrip("/")
        self.model = model
        self.max_history = max_history
        self.city = city
        self.history = []
        self.focus_mode = False
        self._load_history()

    def _load_history(self) -> None:
        """Load chat history from disk so Jarvis remembers previous sessions."""
        if not os.path.isfile(_HISTORY_FILE):
            return
        try:
            with open(_HISTORY_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved, list):
                self.history = saved[-self.max_history * 2:]
        except Exception:
            pass

    def _save_history(self) -> None:
        """Persist chat history to disk."""
        try:
            with open(_HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _context(self) -> dict:
        now = datetime.now()
        today = now.strftime("%A, %d %B %Y")
        time_str = now.strftime("%I:%M %p")
        battery = ""
        try:
            import psutil
            bat = psutil.sensors_battery()
            if bat is not None:
                plugged = "plugged in" if bat.power_plugged else "on battery"
                battery = f" The user's PC battery is at {int(bat.percent)}% and is {plugged}."
        except Exception:
            pass
        city = ""
        if self.city:
            city = f" You live with the user in {self.city}."
        return {"today": today, "time": time_str, "battery": battery, "city": city}

    def _messages(self, user_text: str) -> list:
        ctx = self._context()
        prompt = (
            SYSTEM_PROMPT.replace("__TODAY__", ctx["today"])
            .replace("__TIME__", ctx["time"])
            .replace("__BATTERY__", ctx["battery"])
            .replace("__CITY__", ctx["city"])
        )
        messages = [{"role": "system", "content": prompt}]
        messages.extend(self.history)
        messages.append({"role": "user", "content": user_text})
        return messages

    def ask_stream(self, user_text: str, temperature: float = 0.6) -> Iterator[dict]:
        payload = {
            "model": self.model,
            "messages": self._messages(user_text),
            "stream": True,
            "keep_alive": -1 if self.focus_mode else "30m",
            "options": {"temperature": temperature, "num_ctx": 4096, "num_predict": 200},
        }
        extractor = ReplyExtractor()
        raw = ""
        streamed_reply = ""
        with requests.post(f"{self.url}/api/chat", json=payload, stream=True, timeout=300) as r:
            r.raise_for_status()
            for line in r.iter_lines(decode_unicode=True):
                if not line:
                    continue
                data = json.loads(line)
                if data.get("done"):
                    break
                content = data.get("message", {}).get("content")
                if content:
                    raw += content
                    seg = extractor.feed(content)
                    if seg:
                        streamed_reply += seg
                        yield {"type": "text", "text": seg}
        parsed = self._parse_json(raw)
        reply = streamed_reply or parsed.get("reply", "")
        action = parsed.get("action")
        if isinstance(action, dict):
            name = action.get("name") or action.get("type")
            if name:
                action = {"name": name, "args": action.get("args") or {}}
            else:
                action = None
        else:
            action = None
        yield {"type": "done", "reply": reply, "action": action}

    def commit_turn(self, user_text: str, reply: str, calls: list, results: list) -> None:
        self.history.append({"role": "user", "content": user_text})
        assistant = {"role": "assistant", "content": reply}
        if calls:
            assistant["tool_calls"] = [
                {"function": {"name": c["name"], "arguments": c["args"]}} for c in calls
            ]
        self.history.append(assistant)
        for res in results:
            self.history.append({"role": "tool", "content": res})
        if len(self.history) > self.max_history * 2:
            self.history = self.history[-self.max_history * 2:]
        self._save_history()

    @staticmethod
    def split_sentences(text: str) -> list:
        return [s.strip() for s in _SENT_END.split(text) if s.strip()]

    @staticmethod
    def _parse_json(content: str) -> dict:
        content = re.sub(r"```(?:json)?", "", content).strip()
        start, end = content.find("{"), content.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(content[start:end + 1])
            except json.JSONDecodeError:
                pass
        return {"reply": content, "action": None}

    def ping(self) -> bool:
        try:
            requests.get(f"{self.url}/api/tags", timeout=5)
            return True
        except Exception:
            return False

    def ensure_model(self) -> str:
        tags = requests.get(f"{self.url}/api/tags", timeout=10).json()
        installed = {m["name"] for m in tags.get("models", [])}
        if self.model in installed:
            return "already installed"
        requests.post(f"{self.url}/api/pull", json={"name": self.model}, stream=False, timeout=3600)
        return "installed"