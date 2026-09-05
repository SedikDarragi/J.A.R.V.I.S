import ctypes
import glob
import os
import random
import re
import shutil
import subprocess
import win32clipboard
import threading
import time
import webbrowser
from datetime import datetime
from urllib.parse import quote

import requests

import media
import project
import apps
import steam
import reminder

CITY = ""
LIKED_PLAYLIST_ID = ""
WEB_QUERY = ""
WEB_RESULTS = []
WIZARD_ACTIVE = False
_wizard = None

_app_index = apps.AppIndex()
threading.Thread(target=_app_index.build, daemon=True).start()

WMO_CODES = {
    0: "clear skies",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "foggy",
    48: "icy fog",
    51: "light drizzle",
    53: "drizzle",
    55: "heavy drizzle",
    56: "freezing drizzle",
    57: "heavy freezing drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    66: "freezing rain",
    67: "heavy freezing rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    77: "snow grains",
    80: "light rain showers",
    81: "rain showers",
    82: "violent rain showers",
    85: "snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with hail",
    99: "severe thunderstorm with hail",
}

PLAYLISTS = {
    "random": ["37i9dQZEVXbMDoHDwVN2tF", "37i9dQZF1DXcBWIGoYBM5M", "37i9dQZF1DX0XUsuxWHRQd", "37i9dQZF1DX50QitC6Oqtn", "37i9dQZF1DXcF6B6QPhFDv", "37i9dQZF1DXbwRqtcH5dMK", "37i9dQZEVXbLRQDuF5jeBp", "37i9dQZF1DX8Uebhn9wzrS", "37i9dQZEVXbLuKbNYJZGNS", "37i9dQZF1DX4eRPd2ZHwdh"],
    "rock": ["37i9dQZF1DXcF6B6QPhFDv", "37i9dQZEVXbLRQDuF5jeBp"],
    "pop": ["37i9dQZF1DX50QitC6Oqtn", "37i9dQZF1DXcBWIGoYBM5M"],
    "hiphop": ["37i9dQZF1DX0XUsuxWHRQd"],
    "rap": ["37i9dQZF1DX0XUsuxWHRQd"],
    "chill": ["37i9dQZF1DX8Uebhn9wzrS"],
    "lofi": ["37i9dQZF1DX8Uebhn9wzrS"],
    "workout": ["37i9dQZF1DXbwRqtcH5dMK"],
    "edm": ["37i9dQZEVXbLuKbNYJZGNS"],
    "party": ["37i9dQZF1DX4eRPd2ZHwdh"],
}

APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "file explorer": "explorer.exe",
    "command prompt": "cmd.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "settings": "ms-settings:",
    "task manager": "taskmgr.exe",
    "paint": "mspaint.exe",
    "camera": "start microsoft.windows.camera:",
    "spotify": "spotify",
    "discord": "discord",
    "steam": "steam",
    "whatsapp": "whatsapp",
    "word": "winword.exe",
    "excel": "excel.exe",
    "powerpoint": "powerpnt.exe",
    "edge": "msedge",
    "chrome": "chrome",
    "firefox": "firefox",
    "visual studio code": "vscode",
    "vs code": "vscode",
    "vscode": "vscode",
    "code": "vscode",
    "youtube": "https://www.youtube.com",
}

VK_MEDIA_PLAY_PAUSE = 0xB3
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
USER32 = ctypes.windll.user32

_TIMERS = []


def _shell(cmd: str) -> None:
    subprocess.Popen(f'cmd /c start "" {cmd} 2>nul', shell=True)


def _zen_exe() -> str | None:
    for p in (
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Zen Browser", "zen.exe"),
        r"C:\Program Files\Zen Browser\zen.exe",
        r"C:\Program Files (x86)\Zen Browser\zen.exe",
    ):
        if os.path.exists(p):
            return p
    return None


def _vscode_exe() -> str | None:
    for p in (
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Microsoft VS Code", "Code.exe"),
        r"C:\Program Files\Microsoft VS Code\Code.exe",
        r"C:\Program Files (x86)\Microsoft VS Code\Code.exe",
    ):
        if os.path.exists(p):
            return p
    return None


def _open_url(url: str) -> None:
    exe = _zen_exe()
    if exe:
        subprocess.Popen([exe, url])
    else:
        webbrowser.open(url)


def play_music(args: dict) -> str:
    mode = str(args.get("mode", "liked")).lower()
    genre = str(args.get("genre", "")).lower()

    if mode == "liked":
        if not LIKED_PLAYLIST_ID:
            pid = random.choice(PLAYLISTS["random"])
            uri = f"spotify:playlist:{pid}"
            label = "some tunes"
        else:
            uri = f"spotify:playlist:{LIKED_PLAYLIST_ID}"
            label = "your playlist"
    elif mode == "random":
        ids = PLAYLISTS["random"]
        pid = random.choice(ids)
        uri = f"spotify:playlist:{pid}"
        label = "some random tunes"
    else:
        ids = PLAYLISTS.get(genre) or PLAYLISTS["random"]
        pid = random.choice(ids)
        uri = f"spotify:playlist:{pid}"
        label = f"some {genre} music"

    _shell(uri)
    time.sleep(3.0)
    running = any(p.lower().endswith("spotify.exe") for p in _process_names())
    if not running:
        webbrowser.open(uri.replace("spotify:", "https://open.spotify.com/"))
    if not media.playing():
        media.play()
    if mode == "liked":
        return f"Right away, sir. Playing from {label} on Spotify."
    return f"Right away, sir. {label.capitalize()} coming up on Spotify."


def _process_names():
    try:
        return [p.name().lower() for p in __import__("psutil").process_iter()]
    except Exception:
        return []


def _media_key(code: int) -> None:
    USER32.keybd_event(code, 0, 0, 0)
    USER32.keybd_event(code, 0, 2, 0)


def pause_music(args: dict) -> str:
    if media.session_alive():
        media.pause()
    else:
        _media_key(VK_MEDIA_PLAY_PAUSE)
    return "Music paused, sir."


def resume_music(args: dict) -> str:
    if media.session_alive():
        media.play()
    else:
        _media_key(VK_MEDIA_PLAY_PAUSE)
    return "Music resumed, sir."


def next_track(args: dict) -> str:
    if media.session_alive():
        media.next_track()
    else:
        _media_key(VK_MEDIA_NEXT_TRACK)
    return "Skipping to the next track, sir."


def previous_track(args: dict) -> str:
    if media.session_alive():
        media.previous_track()
    else:
        _media_key(VK_MEDIA_PREV_TRACK)
    return "Going back to the previous track, sir."


_PATH_APPS = {"spotify", "discord", "steam", "whatsapp", "chrome", "firefox"}


def open_app(args: dict) -> str:
    name = str(args.get("name", "")).strip().lower()
    if not name:
        return "I'm afraid you didn't tell me which application, sir."
    if name in _PATH_APPS:
        hit = _app_index.find(name)
        if hit:
            _display, path = hit
            os.startfile(path)
            return f"Opening {_display} for you, sir."
    if name in APPS:
        target = APPS[name]
        if target == "vscode":
            exe = _vscode_exe()
            if exe:
                subprocess.Popen([exe], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
            else:
                _shell("code")
        elif target.startswith("http"):
            _open_url(target)
        else:
            _shell(target)
        return f"Opening {name} for you, sir."
    hit = _app_index.find(name)
    if hit:
        _display, path = hit
        os.startfile(path)
        return f"Opening {_display} for you, sir."
    _shell(name)
    return f"Opening {name} for you, sir."


def open_website(args: dict) -> str:
    url = str(args.get("url", "")).strip()
    if not url:
        return "I need a website address, sir."
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    _open_url(url)
    return f"Opening {url}, sir."


def _fetch_search(query: str) -> list:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
    clean = lambda s: re.sub(r"<[^>]+>", "", s).strip()
    tries = [
        ("https://html.duckduckgo.com/html/", {"q": query}, r'class="result__a"[^>]*>(.*?)</a>', r'class="result__snippet"[^>]*>(.*?)</a>'),
        ("https://lite.duckduckgo.com/lite/", {"q": query}, r'<a rel="nofollow" href="[^"]*"[^>]*>(.*?)</a>', r'<td class="result-snippet">(.*?)</td>'),
        ("https://www.bing.com/search", {"q": query}, r'<h2><a href="[^"]*"[^>]*>(.*?)</a></h2>', r'<p[^>]*>(.*?)</p>'),
    ]
    for url, params, tp, sp in tries:
        try:
            r = requests.get(url, params=params, headers=headers, timeout=10)
            titles = re.findall(tp, r.text)
            snippets = re.findall(sp, r.text)
            items = []
            for i, t in enumerate(titles[:5]):
                sn = clean(snippets[i]) if i < len(snippets) else ""
                items.append(f"- {clean(t)}" + (f": {sn}" if sn else ""))
            if items:
                return items
        except Exception:
            continue
    return []


FIAT = {
    "dollar": "USD", "dollars": "USD", "usd": "USD", "us": "USD", "american": "USD",
    "euro": "EUR", "euros": "EUR", "eur": "EUR",
    "pound": "GBP", "pounds": "GBP", "gbp": "GBP", "british pound": "GBP",
    "dinar": "TND", "dinars": "TND", "tnd": "TND", "tunisian dinar": "TND", "tunisian dinars": "TND", "tunisian": "TND",
    "yen": "JPY", "jpy": "JPY", "yuan": "CNY", "cny": "CNY", "renminbi": "CNY",
    "cad": "CAD", "canadian": "CAD", "aud": "AUD", "australian": "AUD", "chf": "CHF", "swiss franc": "CHF",
    "aed": "AED", "dirham": "AED", "sar": "SAR", "riyal": "SAR", "egp": "EGP", "egyptian pound": "EGP",
    "mad": "MAD", "moroccan dirham": "MAD", "try": "TRY", "lira": "TRY", "inr": "INR", "rupee": "INR",
}

CRYPTO = {
    "bitcoin": "bitcoin", "btc": "bitcoin",
    "ethereum": "ethereum", "eth": "ethereum",
    "solana": "solana", "sol": "solana",
    "dogecoin": "dogecoin", "doge": "dogecoin",
    "xrp": "ripple", "cardano": "cardano", "ada": "cardano",
}


def _norm_cur(raw: str) -> str:
    s = raw.strip().lower()
    if s in FIAT:
        return FIAT[s]
    if s in CRYPTO:
        return CRYPTO[s]
    return s.upper()


def convert_currency(args: dict) -> str:
    from_c = _norm_cur(str(args.get("from", "")))
    to_c = _norm_cur(str(args.get("to", "")))
    if not from_c or not to_c:
        return "Which currencies would you like me to convert, sir?"
    try:
        amount = float(args.get("amount") or 1)
    except (TypeError, ValueError):
        amount = 1.0
    try:
        if from_c in CRYPTO.values() or to_c in CRYPTO.values():
            if from_c in CRYPTO.values():
                r = requests.get(
                    "https://api.coingecko.com/api/v3/simple/price",
                    params={"ids": from_c, "vs_currencies": to_c.lower()},
                    timeout=15,
                ).json()
                rate = r.get(from_c, {}).get(to_c.lower())
            else:
                r = requests.get(
                    "https://api.coingecko.com/api/v3/simple/price",
                    params={"ids": to_c, "vs_currencies": from_c.lower()},
                    timeout=15,
                ).json()
                inv = r.get(to_c, {}).get(from_c.lower())
                rate = 1.0 / inv if inv else None
        else:
            r = requests.get(f"https://open.er-api.com/v6/latest/{from_c}", timeout=15).json()
            rate = r.get("rates", {}).get(to_c)
        if rate is None:
            return f"I'm afraid I couldn't find a rate for {from_c} to {to_c}, sir."
    except Exception:
        return "I'm afraid I couldn't reach the exchange service, sir."
    total = amount * rate
    if amount == 1:
        return f"One {from_c} is currently about {rate:.2f} {to_c}, sir."
    return f"{amount:g} {from_c} is about {total:.2f} {to_c}, sir."


def begin_wizard() -> str:
    global WIZARD_ACTIVE, _wizard
    _wizard = project.ProjectWizard()
    WIZARD_ACTIVE = True
    return _wizard.start()


def new_project(args: dict) -> str:
    return begin_wizard()


def project_feed(text: str):
    global WIZARD_ACTIVE, _wizard
    if _wizard is None:
        WIZARD_ACTIVE = False
        return None
    kind, msg = _wizard.answer(text)
    if kind in ("done", "cancel"):
        WIZARD_ACTIVE = False
        _wizard = None
    return msg


def _launch_vscode(folder: str) -> None:
    exe = _vscode_exe()
    if exe:
        subprocess.Popen([exe, "--new-window", folder], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
        return
    shims = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Microsoft VS Code", "bin", "code.cmd"),
        r"C:\Program Files\Microsoft VS Code\bin\code.cmd",
        r"C:\Program Files (x86)\Microsoft VS Code\bin\code.cmd",
    ]
    for shim in shims:
        if os.path.exists(shim):
            subprocess.Popen(f'cmd /c ""{shim}" --new-window "{folder}""', shell=True)
            return
    subprocess.Popen(f'cmd /c start "" code --new-window "{folder}"', shell=True)


def _launch_opencode(folder: str, name: str) -> None:
    subprocess.Popen(
        ["powershell", "-NoProfile", "-Command",
         f"Start-Process cmd -ArgumentList '/k','opencode' -WorkingDirectory '{folder}'"],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


project.LAUNCH_VSCODE = _launch_vscode
project.LAUNCH_OPENCODE = _launch_opencode


def web_search(args: dict) -> str:
    global WEB_QUERY, WEB_RESULTS
    query = str(args.get("query", "")).strip()
    if not query:
        return "What would you like me to search for, sir?"
    background = bool(args.get("background", False))
    WEB_QUERY = query
    WEB_RESULTS = _fetch_search(query)
    if not background:
        _open_url(f"https://www.google.com/search?q={quote(query)}")
    if WEB_RESULTS:
        return ""
    return f"Searching the web for {query}, sir."


def play_youtube(args: dict) -> str:
    query = str(args.get("query", "")).strip()
    if not query:
        return "What video would you like me to find, sir?"
    _open_url(f"https://www.youtube.com/results?search_query={quote(query)}")
    return f"Finding {query} on YouTube for you, sir."


def _endpoint_volume():
    from pycaw.pycaw import AudioUtilities
    return AudioUtilities.GetSpeakers().EndpointVolume


def set_volume(args: dict) -> str:
    try:
        volume = _endpoint_volume()
        level = max(0, min(100, int(args.get("level", 50))))
        volume.SetMasterVolumeLevelScalar(level / 100.0, None)
        return f"Volume set to {level} percent, sir."
    except Exception:
        return "I'm afraid I couldn't adjust the volume, sir."


def mute(args: dict) -> str:
    try:
        _endpoint_volume().SetMute(1, None)
        return "Muted, sir."
    except Exception:
        return "I couldn't mute the system, sir."


def unmute(args: dict) -> str:
    try:
        _endpoint_volume().SetMute(0, None)
        return "Unmuted, sir."
    except Exception:
        return "I couldn't unmute the system, sir."


def lock_pc(args: dict) -> str:
    subprocess.Popen("rundll32.exe user32.dll,LockWorkStation")
    return "Locking the computer, sir."


def take_screenshot(args: dict) -> str:
    try:
        from PIL import ImageGrab
        folder = os.path.join(os.path.expanduser("~"), "Pictures", "Jarvis")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        ImageGrab.grab().save(path)
        return f"Screenshot saved to Pictures, sir."
    except Exception:
        return "I couldn't take a screenshot, sir."


def _timer_done(minutes: int, speak) -> None:
    import winsound
    for _ in range(3):
        winsound.MessageBeep()
        time.sleep(0.4)
    if speak:
        speak(f"Sir, your {minutes} minute timer has finished.")


def set_timer(args: dict) -> str:
    minutes = int(args.get("minutes", 0))
    if minutes <= 0:
        return "How many minutes should I set the timer for, sir?"
    t = threading.Thread(target=_timer_done, args=(minutes, None), daemon=True)
    _TIMERS.append(t)
    t.start()
    return f"Timer set for {minutes} minute{'s' if minutes != 1 else ''}, sir."


def weather(args: dict) -> str:
    city = str(args.get("city", "")).strip() or CITY
    if not city:
        return "I don't know your city, sir. Tell me the city name and I'll check the forecast."
    try:
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "en", "format": "json"},
            timeout=15,
        ).json()
        results = geo.get("results") or []
        if not results:
            return f"I couldn't find a place called {city}, sir."
        place = results[0]
        f = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": "temperature_2m,weather_code,wind_speed_10m",
                "temperature_unit": "celsius",
            },
            timeout=15,
        ).json()
        cur = f["current"]
        code = WMO_CODES.get(cur["weather_code"], "unusual weather")
        temp = round(cur["temperature_2m"])
        wind = round(cur["wind_speed_10m"])
        return (f"The weather in {place['name']} right now is {temp} degrees with {code}, "
                f"and a wind speed of {wind} kilometres per hour.")
    except Exception:
        return "I'm afraid I couldn't reach the weather service, sir."


def launch_game(args: dict) -> str:
    name = args.get("name", "").strip()
    if not name:
        return "Which game should I launch, sir?"
    mgr = steam.get_manager()
    game = mgr.find_game(name)
    print(f"  [steam] find_game('{name}') -> {game}")
    if not game:
        return f"I couldn't find {name} on Steam, sir."
    installed = mgr.is_installed(game["appid"])
    print(f"  [steam] appid={game['appid']} installed={installed}")
    if not installed:
        result = mgr.install(game["appid"])
        print(f"  [steam] install result: {result}")
        return result
    return mgr.launch(game["appid"])


def install_game(args: dict) -> str:
    name = args.get("name", "").strip()
    if not name:
        return "Which game should I install, sir?"
    mgr = steam.get_manager()
    game = mgr.find_game(name)
    if not game:
        return f"I couldn't find {name} in the Steam store, sir."
    if mgr.is_installed(game["appid"]):
        return f"{game['name']} is already installed, sir."
    return mgr.install(game["appid"])


def set_reminder(args: dict) -> str:
    message = args.get("message", "").strip()
    if not message:
        return "What should I remind you about, sir?"
    # Accept seconds, minutes, or hours — convert all to seconds
    seconds = int(args.get("seconds", 0))
    minutes = int(args.get("minutes", 0))
    hours = int(args.get("hours", 0))
    total_seconds = seconds + (minutes * 60) + (hours * 3600)
    if total_seconds <= 0:
        return "Please tell me when to remind you, sir."
    mgr = reminder.get_manager()
    return mgr.add(total_seconds, message)


def list_reminders(args: dict) -> str:
    return reminder.get_manager().list_reminders()


def cancel_reminders(args: dict) -> str:
    return reminder.get_manager().cancel_all()


def copy_to_clipboard(args: dict) -> str:
    text = args.get("text", "").strip()
    if not text:
        return "What should I copy to the clipboard, sir?"
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
    finally:
        win32clipboard.CloseClipboard()
    return f"Copied to clipboard: {text[:80]}{'...' if len(text) > 80 else ''}"


def read_clipboard(args: dict) -> str:
    win32clipboard.OpenClipboard()
    try:
        text = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
    except Exception:
        text = ""
    finally:
        win32clipboard.CloseClipboard()
    if not text.strip():
        return "The clipboard is empty, sir."
    return f"Clipboard contains: {text[:200]}{'...' if len(text) > 200 else ''}"


def clear_clipboard(args: dict) -> str:
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
    finally:
        win32clipboard.CloseClipboard()
    return "Clipboard cleared, sir."


_BLOCKED_DIRS = {
    os.path.normpath(p) for p in [
        "C:\\Windows", "C:\\Program Files", "C:\\Program Files (x86)",
        "C:\\ProgramData", "C:\\Recovery", "C:\\$Recycle.Bin",
        "C:\\System Volume Information",
    ]
}

_cwd = os.path.expanduser("~")


def _safe_path(path: str) -> str | None:
    """Resolve path relative to _cwd and block dangerous directories."""
    expanded = os.path.expanduser(path)
    if os.path.isabs(expanded):
        full = os.path.normpath(expanded)
    else:
        full = os.path.normpath(os.path.join(_cwd, expanded))
    for blocked in _BLOCKED_DIRS:
        if full.startswith(blocked):
            return None
    return full


def change_directory(args: dict) -> str:
    global _cwd
    path = args.get("path", "").strip()
    if not path:
        return "Where should I go, sir?"
    if path in ("~", "home"):
        path = "~"
    expanded = os.path.expanduser(path)
    if os.path.isabs(expanded):
        target = os.path.normpath(expanded)
    else:
        target = os.path.normpath(os.path.join(_cwd, expanded))
    if not os.path.isdir(target):
        return f"Directory not found: {path}"
    for blocked in _BLOCKED_DIRS:
        if target.startswith(blocked):
            return "I can't go there, sir."
    _cwd = target
    return f"Now in {_cwd}"


def get_current_directory(args: dict) -> str:
    return f"Currently in {_cwd}, sir."


def read_file(args: dict) -> str:
    path = args.get("path", "").strip()
    if not path:
        return "Which file should I read, sir?"
    safe = _safe_path(path)
    if not safe:
        return "I can't access that directory, sir."
    if not os.path.isfile(safe):
        return f"File not found: {path}"
    try:
        with open(safe, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(4000)
        if len(content) == 4000:
            content += "\n... (truncated)"
        return f"Contents of {os.path.basename(safe)}:\n{content}"
    except Exception:
        return f"Could not read {path}, sir."


def write_file(args: dict) -> str:
    path = args.get("path", "").strip()
    content = args.get("content", "")
    if not path:
        return "Where should I write the file, sir?"
    safe = _safe_path(path)
    if not safe:
        return "I can't write to that directory, sir."
    try:
        os.makedirs(os.path.dirname(safe), exist_ok=True)
        with open(safe, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Written to {os.path.basename(safe)}, sir."
    except Exception:
        return f"Could not write to {path}, sir."


def delete_file(args: dict) -> str:
    path = args.get("path", "").strip()
    if not path:
        return "Which file should I delete, sir?"
    safe = _safe_path(path)
    if not safe:
        return "I can't delete files from that directory, sir."
    if not os.path.exists(safe):
        return f"File not found: {path}"
    try:
        if os.path.isdir(safe):
            shutil.rmtree(safe)
            return f"Deleted folder {os.path.basename(safe)}, sir."
        os.remove(safe)
        return f"Deleted {os.path.basename(safe)}, sir."
    except Exception:
        return f"Could not delete {path}, sir."


def list_files(args: dict) -> str:
    path = args.get("path", "").strip() or "."
    safe = _safe_path(path)
    if not safe:
        return "I can't access that directory, sir."
    if not os.path.isdir(safe):
        return f"Not a directory: {path}"
    try:
        entries = os.listdir(safe)
        if not entries:
            return "That folder is empty, sir."
        folders = [e + "/" for e in entries if os.path.isdir(os.path.join(safe, e))]
        files = [e for e in entries if os.path.isfile(os.path.join(safe, e))]
        parts = folders[:15] + files[:15]
        total = len(folders) + len(files)
        result = "\n".join(parts)
        if total > 30:
            result += f"\n... and {total - 30} more"
        return f"Contents of {os.path.basename(safe) or path}:\n{result}"
    except Exception:
        return f"Could not list {path}, sir."


def copy_file(args: dict) -> str:
    src = args.get("source", "").strip()
    dst = args.get("destination", "").strip()
    if not src or not dst:
        return "I need a source and destination, sir."
    safe_src = _safe_path(src)
    safe_dst = _safe_path(dst)
    if not safe_src or not safe_dst:
        return "I can't access that path, sir."
    if not os.path.exists(safe_src):
        return f"Source not found: {src}"
    try:
        if os.path.isdir(safe_src):
            shutil.copytree(safe_src, safe_dst)
        else:
            os.makedirs(os.path.dirname(safe_dst), exist_ok=True)
            shutil.copy2(safe_src, safe_dst)
        return f"Copied to {os.path.basename(safe_dst)}, sir."
    except Exception:
        return f"Could not copy {src}, sir."


def move_file(args: dict) -> str:
    src = args.get("source", "").strip()
    dst = args.get("destination", "").strip()
    if not src or not dst:
        return "I need a source and destination, sir."
    safe_src = _safe_path(src)
    safe_dst = _safe_path(dst)
    if not safe_src or not safe_dst:
        return "I can't access that path, sir."
    if not os.path.exists(safe_src):
        return f"Source not found: {src}"
    try:
        os.makedirs(os.path.dirname(safe_dst), exist_ok=True)
        shutil.move(safe_src, safe_dst)
        return f"Moved to {os.path.basename(safe_dst)}, sir."
    except Exception:
        return f"Could not move {src}, sir."


HANDLERS = {
    "play_music": play_music,
    "pause_music": pause_music,
    "resume_music": resume_music,
    "next_track": next_track,
    "previous_track": previous_track,
    "open_app": open_app,
    "open_website": open_website,
    "web_search": web_search,
    "play_youtube": play_youtube,
    "convert_currency": convert_currency,
    "set_volume": set_volume,
    "mute": mute,
    "unmute": unmute,
    "deafen": mute,
    "undeafen": unmute,
    "lock_pc": lock_pc,
    "take_screenshot": take_screenshot,
    "set_timer": set_timer,
    "weather": weather,
    "new_project": new_project,
    "launch_game": launch_game,
    "install_game": install_game,
    "set_reminder": set_reminder,
    "list_reminders": list_reminders,
    "cancel_reminders": cancel_reminders,
    "copy_to_clipboard": copy_to_clipboard,
    "read_clipboard": read_clipboard,
    "clear_clipboard": clear_clipboard,
    "read_file": read_file,
    "write_file": write_file,
    "delete_file": delete_file,
    "list_files": list_files,
    "copy_file": copy_file,
    "move_file": move_file,
    "change_directory": change_directory,
    "get_current_directory": get_current_directory,
}


def run_action(name: str, args: dict) -> str:
    handler = HANDLERS.get(name)
    if handler is None:
        return f"I don't know how to do that yet, sir."
    try:
        return handler(args or {})
    except Exception:
        return f"I'm afraid something went wrong while doing that, sir."
