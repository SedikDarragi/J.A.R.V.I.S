import os
import subprocess

_BASE = os.path.dirname(os.path.abspath(__file__))
_SCRIPT = os.path.join(_BASE, "media.ps1")


def _run(cmd: str) -> str:
    try:
        p = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", _SCRIPT, cmd],
            capture_output=True,
            timeout=25,
        )
        out = p.stdout or b""
        if out[:2] in (b"\xff\xfe", b"\xfe\xff"):
            return out.decode("utf-16-le", errors="replace")
        return out.decode("utf-8", errors="replace")
    except Exception:
        return ""


def session_alive() -> bool:
    return "STATUS=" in _run("status")


def playing() -> bool:
    out = _run("status").lower()
    for line in out.splitlines():
        if line.startswith("status="):
            return "playing" in line
    return False


def play() -> bool:
    return "OK" in _run("play")


def pause() -> bool:
    return "OK" in _run("pause")


def toggle() -> bool:
    return "OK" in _run("toggle")


def next_track() -> bool:
    return "OK" in _run("next")


def previous_track() -> bool:
    return "OK" in _run("prev")