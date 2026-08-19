import os
import re
import subprocess

DEFAULT_LOCATION = r"C:\Users\Admin\Documents\info\projects"

MODEL_ALIASES = {
    "deepseek": "opencode/deepseek-v4-flash-free",
    "deep seek": "opencode/deepseek-v4-flash-free",
    "deepseek free": "opencode/deepseek-v4-flash-free",
    "free": "opencode/deepseek-v4-flash-free",
    "free one": "opencode/deepseek-v4-flash-free",
    "the free one": "opencode/deepseek-v4-flash-free",
    "default": "opencode/deepseek-v4-flash-free",
}

LAUNCH_VSCODE = None
LAUNCH_OPENCODE = None

_STEPS = [
    ("name", "What shall we call the project, sir?"),
    ("type", "What kind of project is it - a web app, a Python tool, a Node service, or something else?"),
    ("location", "Where should I create it, sir? Say \"default\" for your projects folder, or give me a full path."),
    ("model", "And which AI model should opencode use - the free deepseek one, or another model?"),
]

_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


_NAME_PATTERNS = [
    r"\bcall\s+it\s+",
    r"\bcall\s+the\s+project\s+",
    r"\bit(?:'s| is)?\s+called\s+",
    r"\bis\s+called\s+",
    r"\bthe\s+(?:project\s+)?name\s+is\s+",
    r"\bname\s+it\s+",
    r"\b(?:we(?:'ll| will| would)?|lets|let'?s)\s+(?:call|name)\s+(?:it|the project|this)\s+",
]

_LOCATION_PATTERNS = [
    r"\bput\s+it\s+in\s+",
    r"\bput\s+it\s+at\s+",
    r"\bcreate\s+it\s+(?:in|at)\s+",
    r"\bmake\s+it\s+in\s+",
    r"\bstore\s+it\s+in\s+",
    r"\bsave\s+it\s+in\s+",
]


def _extract_after(text: str, patterns: list) -> str:
    cut = None
    for pat in patterns:
        m = re.search(pat, text)
        if m and (cut is None or m.end() > cut):
            cut = m.end()
    return text[cut:] if cut is not None else text


def _sanitize_name(raw: str) -> str:
    name = _extract_after(raw, _NAME_PATTERNS)
    name = re.sub(r"^(?:the|a|an)\s+", "", name)
    name = re.sub(r"\s+(?:please|for me|thanks|thank you|okay|ok|then)\s*$", "", name)
    name = name.strip().strip("'\".,;:!?")
    name = _ILLEGAL.sub("", name).strip().strip(". ")
    return name


def _resolve_location(raw: str) -> str:
    s = _extract_after(raw.strip(), _LOCATION_PATTERNS).strip().strip('"').strip()
    low = s.lower()
    if low in ("default", "default location", "projects", "projects folder", "usual", "the usual"):
        return DEFAULT_LOCATION
    if low in ("desktop", "my desktop"):
        return os.path.join(os.path.expanduser("~"), "Desktop")
    if low in ("documents", "my documents"):
        return os.path.join(os.path.expanduser("~"), "Documents")
    return os.path.expandvars(os.path.expanduser(s))


def _resolve_model(raw: str) -> str:
    key = raw.strip().lower()
    if key in MODEL_ALIASES:
        return MODEL_ALIASES[key]
    if "deepseek" in key or "free" in key:
        return "opencode/deepseek-v4-flash-free"
    if "claude" in key:
        return "anthropic/claude-sonnet-4"
    if "gpt" in key or "chatgpt" in key:
        return "openai/gpt-5"
    if "gemini" in key:
        return "google/gemini-3-pro"
    return key


class ProjectWizard:
    def __init__(self):
        self.answers = {}
        self.step = 0
        self.cancelled = False

    def start(self) -> str:
        self.answers = {}
        self.step = 0
        self.cancelled = False
        return _STEPS[0][1]

    def _question(self):
        if self.step < len(_STEPS):
            return _STEPS[self.step][1]
        return None

    def answer(self, text: str):
        text = (text or "").strip()
        if text.lower() in ("cancel", "cancel that", "nevermind", "never mind", "stop", "abort", "forget it", "skip this"):
            self.cancelled = True
            return ("cancel", "Very well, sir. We'll set that aside for now.")
        if self.step >= len(_STEPS):
            return ("done", self._finish())
        key = _STEPS[self.step][0]
        if key == "name":
            clean = _sanitize_name(text)
            if not clean:
                return ("ask", "I need a name to work with, sir. What shall we call the project?")
            self.answers[key] = clean
        elif key == "location":
            loc = _resolve_location(text)
            if not loc:
                return ("ask", "I didn't quite catch the location, sir. A full path, or say \"default\".")
            self.answers[key] = loc
        elif key == "model":
            self.answers[key] = _resolve_model(text)
        else:
            self.answers[key] = text
        self.step += 1
        q = self._question()
        if q:
            return ("ask", q)
        return ("done", self._finish())

    def _finish(self) -> str:
        name = self.answers.get("name", "untitled")
        loc = self.answers.get("location") or DEFAULT_LOCATION
        model = self.answers.get("model") or "opencode/deepseek-v4-flash-free"
        try:
            os.makedirs(loc, exist_ok=True)
            folder = os.path.join(loc, name)
            os.makedirs(folder, exist_ok=True)
            with open(os.path.join(folder, "opencode.json"), "w", encoding="utf-8") as f:
                f.write('{\n  "$schema": "https://opencode.ai/config.json",\n  "model": "%s"\n}\n' % model)
            if LAUNCH_VSCODE:
                LAUNCH_VSCODE(folder)
            if LAUNCH_OPENCODE:
                LAUNCH_OPENCODE(folder, name)
            return (f"Project {name} is ready at {folder}, sir. Visual Studio Code is opening, "
                    f"and opencode is starting with the {model} model.")
        except Exception as e:
            return f"I'm afraid something went wrong creating the project, sir: {e}"