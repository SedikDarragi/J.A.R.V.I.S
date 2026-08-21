import os
import re

_START_DIRS = [
    os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs"),
    r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
]


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", s.lower())


class AppIndex:
    def __init__(self):
        self.entries = []
        self.built = False

    def build(self) -> None:
        entries = []
        seen = set()
        for d in _START_DIRS:
            if not os.path.isdir(d):
                continue
            for root, _dirs, files in os.walk(d):
                for f in files:
                    if not f.lower().endswith(".lnk"):
                        continue
                    name = os.path.splitext(f)[0]
                    if name.lower() in seen:
                        continue
                    seen.add(name.lower())
                    entries.append((_norm(name), name, os.path.join(root, f)))
        self.entries = entries
        self.built = True

    def find(self, query: str):
        q = _norm(query)
        if not q:
            return None
        qw = [w for w in q.split() if w]
        best = None
        for norm, name, target in self.entries:
            score = 0
            if norm == q:
                score = 100
            elif norm.startswith(q):
                score = 80
            elif q in norm:
                score = 60
            elif qw and all(w in norm for w in qw):
                score = 45
            elif qw and any(w in norm for w in qw):
                score = 30
            words = norm.split()
            if q in words:
                score = max(score, 90)
            if score and words and words[-1] == q:
                score += 15
            if score and (best is None or score > best[0]):
                best = (score, name, target)
        if best:
            return best[1], best[2]
        return None