import ctypes
import os
import random
import subprocess
import threading
import time
import webbrowser
from datetime import datetime
from urllib.parse import quote

import requests

import media

CITY = ""
LIKED_PLAYLIST_ID = ""

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
    "vs code": "code",
    "youtube": "https://www.youtube.com",
}

VK_MEDIA_PLAY_PAUSE = 0xB3
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
USER32 = ctypes.windll.user32

_TIMERS = []


def _shell(cmd: str) -> None:
    subprocess.Popen(f'cmd /c start "" {cmd}', shell=True)


def play_music(args: dict) -> str:
    mode = str(args.get("mode", "liked")).lower()
    genre = str(args.get("genre", "")).lower()

    if mode == "liked":
        if not LIKED_PLAYLIST_ID:
            return "I don't have your playlist set up yet, sir. Point me to it and I'll play it for you."
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


def open_app(args: dict) -> str:
    name = str(args.get("name", "")).strip().lower()
    if not name:
        return "I'm afraid you didn't tell me which application, sir."
    target = APPS.get(name)
    if target is None:
        target = name
    if target.startswith("http"):
        webbrowser.open(target)
    elif target.startswith("start "):
        _shell(target)
    else:
        _shell(target)
    return f"Opening {name} for you, sir."


def open_website(args: dict) -> str:
    url = str(args.get("url", "")).strip()
    if not url:
        return "I need a website address, sir."
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    webbrowser.open(url)
    return f"Opening {url}, sir."


def web_search(args: dict) -> str:
    query = str(args.get("query", "")).strip()
    if not query:
        return "What would you like me to search for, sir?"
    webbrowser.open(f"https://www.google.com/search?q={quote(query)}")
    return f"Searching the web for {query}, sir."


def play_youtube(args: dict) -> str:
    query = str(args.get("query", "")).strip()
    if not query:
        return "What video would you like me to find, sir?"
    webbrowser.open(f"https://www.youtube.com/results?search_query={quote(query)}")
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
    "set_volume": set_volume,
    "mute": mute,
    "unmute": unmute,
    "lock_pc": lock_pc,
    "take_screenshot": take_screenshot,
    "set_timer": set_timer,
    "weather": weather,
}


def run_action(name: str, args: dict) -> str:
    handler = HANDLERS.get(name)
    if handler is None:
        return f"I don't know how to do that yet, sir."
    try:
        return handler(args or {})
    except Exception:
        return f"I'm afraid something went wrong while doing that, sir."
