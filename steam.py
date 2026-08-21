import os
import re
import glob
import subprocess
import time
import urllib.parse

try:
    import requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

# ---------------------------------------------------------------------------
# Steam game manager – discovers installed games, launches & installs via
# the steam:// URI protocol.  Works with any Windows Steam install.
# ---------------------------------------------------------------------------

# Common abbreviations -> official game names (add more as needed)
_ALIASES = {
    "cod": "call of duty",
    "ffxiv": "final fantasy xiv",
    "wow": "world of warcraft",
    "ow": "overwatch",
    "ow2": "overwatch",
    "mhw": "monster hunter world",
    "hr": "helldivers",
    "drg": "deep rock galactic",
    "nms": "no mans sky",
    "warframe": "warframe",
}


class SteamManager:
    """Discovers Steam games on this PC and can launch / install them."""

    def __init__(self):
        self._steam_path: str | None = None
        self._games: dict[str, dict] = {}   # appid -> {name, appid, installed}
        self._name_index: dict[str, str] = {}  # normalised name -> appid
        self._find_steam()
        self._scan_games()

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def _find_steam(self) -> None:
        candidates = [
            r"C:\Program Files (x86)\Steam",
            r"C:\Program Files\Steam",
            r"D:\Steam",
            r"D:\Program Files (x86)\Steam",
            r"E:\Steam",
            r"E:\Program Files (x86)\Steam",
        ]
        for p in candidates:
            if os.path.isdir(p) and os.path.isfile(os.path.join(p, "steam.exe")):
                self._steam_path = p
                return
        try:
            import winreg
            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    key = winreg.OpenKey(hive, r"Software\Valve\Steam")
                    self._steam_path = winreg.QueryValueEx(key, "SteamPath")[0]
                    return
                except OSError:
                    pass
        except ImportError:
            pass

    def _scan_games(self) -> None:
        if not self._steam_path:
            return
        for lib_dir in self._library_dirs():
            steamapps = os.path.join(lib_dir, "steamapps")
            if not os.path.isdir(steamapps):
                continue
            for manifest in glob.glob(os.path.join(steamapps, "appmanifest_*.acf")):
                self._parse_manifest(manifest)

    def _library_dirs(self) -> list[str]:
        vdf = os.path.join(self._steam_path, "steamapps", "libraryfolders.vdf")
        dirs = {self._steam_path}
        if not os.path.isfile(vdf):
            return list(dirs)
        with open(vdf, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        for match in re.finditer(r'"path"\s+"([^"]+)"', text):
            p = match.group(1).replace("\\\\", "\\")
            if os.path.isdir(p):
                dirs.add(p)
        return list(dirs)

    def _parse_manifest(self, path: str) -> None:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            return
        appid = name = ""
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.startswith('"appid"'):
                appid = self._extract_val(stripped)
            elif stripped.startswith('"name"'):
                name = self._extract_val(stripped)
        if not appid or not name:
            return
        # Clean garbled unicode (e.g. trademark symbols)
        name = name.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
        name = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", name).strip()
        self._games[appid] = {"name": name, "appid": appid, "installed": True}
        normed = self._norm(name)
        self._name_index[normed] = appid
        # Also index individual words for partial matching (e.g. "overwatch")
        for word in normed.split():
            if len(word) > 2 and word not in self._name_index:
                self._name_index[word] = appid

    @staticmethod
    def _extract_val(line: str) -> str:
        """Pull the value from a VDF line like:  "key"  \t  "value" """
        parts = line.split('"')
        if len(parts) >= 4:
            return parts[3].strip()
        return ""

    # ------------------------------------------------------------------
    # Fuzzy matching
    # ------------------------------------------------------------------

    @staticmethod
    def _norm(name: str) -> str:
        name = name.lower().strip()
        name = re.sub(r"[^\w\s]", "", name)
        name = re.sub(r"\s+", " ", name)
        return name

    def find_game(self, query: str) -> dict | None:
        q = self._norm(query)
        # Resolve abbreviations
        q = _ALIASES.get(q, q)
        # Exact match
        if q in self._name_index:
            return self._games[self._name_index[q]]
        # Check each word of query individually
        for word in q.split():
            if word in self._name_index:
                return self._games[self._name_index[word]]
        # Starts-with
        for norm, appid in self._name_index.items():
            if norm.startswith(q) or q.startswith(norm):
                return self._games[appid]
        # Substring
        for norm, appid in self._name_index.items():
            if q in norm or norm in q:
                return self._games[appid]
        # Word overlap
        q_words = set(q.split())
        best, best_score = None, 0
        for norm, appid in self._name_index.items():
            g_words = set(norm.split())
            overlap = len(q_words & g_words)
            if overlap > best_score:
                best_score = overlap
                best = self._games[appid]
        if best and best_score > 0:
            return best
        # Fallback: search the Steam Store API
        return self._search_store(query)

    # ------------------------------------------------------------------
    # Steam Store search (for games not yet installed)
    # ------------------------------------------------------------------

    @staticmethod
    def _search_store(query: str) -> dict | None:
        """Search store.steampowered.com for a game by name. Returns dict or None."""
        if not _HAS_REQUESTS:
            return None
        try:
            url = f"https://store.steampowered.com/api/storesearch/?term={urllib.parse.quote(query)}&l=english&cc=US"
            r = requests.get(url, timeout=8)
            data = r.json()
            items = data.get("items", [])
            if not items:
                return None
            # Pick the first result
            item = items[0]
            appid = str(item.get("id", ""))
            name = item.get("name", "")
            if appid and name:
                return {"name": name, "appid": appid, "installed": False}
        except Exception:
            pass
        return None

    def list_games(self) -> list[dict]:
        return sorted(self._games.values(), key=lambda g: g["name"].lower())

    # ------------------------------------------------------------------
    # Launch / Install
    # ------------------------------------------------------------------

    def _ensure_steam_running(self) -> bool:
        """Start Steam if not running, wait until it's ready."""
        if self._steam_is_running():
            return True
        # Start Steam
        if self._steam_path:
            exe = os.path.join(self._steam_path, "steam.exe")
            if os.path.isfile(exe):
                subprocess.Popen([exe], cwd=self._steam_path)
                # Wait up to 15 seconds for Steam to appear in process list
                for _ in range(30):
                    time.sleep(0.5)
                    if self._steam_is_running():
                        # Give Steam a moment to register its URI handler
                        time.sleep(2)
                        return True
        return False

    @staticmethod
    def _steam_is_running() -> bool:
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq steam.exe"],
                capture_output=True, text=True, timeout=5,
            )
            return "steam.exe" in result.stdout.lower()
        except Exception:
            return False

    def launch(self, appid: str) -> str:
        game = self._games.get(appid)
        if not game:
            return f"Game with appid {appid} not found."
        self._ensure_steam_running()
        try:
            os.startfile(f"steam://rungameid/{appid}")
            return f"Launching {game['name']}, sir."
        except Exception as e:
            return f"Failed to launch {game['name']}: {e}"

    def install(self, appid: str) -> str:
        game = self._games.get(appid)
        if not game:
            return f"Game with appid {appid} not found."
        self._ensure_steam_running()
        try:
            os.startfile(f"steam://install/{appid}")
            return f"Starting download for {game['name']}, sir."
        except Exception as e:
            return f"Failed to start download for {game['name']}: {e}"

    def is_installed(self, appid: str) -> bool:
        return appid in self._games


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_manager: SteamManager | None = None

def get_manager() -> SteamManager:
    global _manager
    if _manager is None:
        _manager = SteamManager()
    return _manager
