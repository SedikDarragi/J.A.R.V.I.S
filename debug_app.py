import subprocess, sys, os, traceback

BASE = r"C:\Users\Admin\Documents\info\projects\Jarvis"
out = []

out.append("=== modules ===")
for name in ["main", "actions", "brain", "stt", "tts", "media"]:
    try:
        p = subprocess.run(
            [sys.executable, "-c", f"import {name}; print('OK')"],
            cwd=BASE, capture_output=True, text=True, timeout=60,
        )
        line = p.stdout.strip() or p.stderr.strip()[:200]
        out.append(f"{name}: {line}")
    except Exception as e:
        out.append(f"{name}: error {e!r}")

out.append("=== key features present ===")
try:
    p = subprocess.run([sys.executable, "-c", """
import actions, brain
checks = {
    "convert_currency": "def convert_currency" in open(r'C:\\Users\\Admin\\Documents\\info\\projects\\Jarvis\\actions.py', encoding='utf-8').read(),
    "vscode action": "vscode" in open(r'C:\\Users\\Admin\\Documents\\info\\projects\\Jarvis\\actions.py', encoding='utf-8').read(),
    "prompt has vscode": "visual studio code|vs code" in brain.SYSTEM_PROMPT,
    "prompt has retry examples": "jarvis open code" in brain.SYSTEM_PROMPT,
    "temperature param": "temperature: float = 0.6" in open(r'C:\\Users\\Admin\\Documents\\info\\projects\\Jarvis\\brain.py', encoding='utf-8').read(),
}
for k, v in checks.items():
    print(f"{k}: {v}")
"""], cwd=BASE, capture_output=True, text=True, timeout=60)
    out.append(p.stdout.strip() or p.stderr.strip()[:300])
except Exception as e:
    out.append("error " + repr(e))

out.append("=== ollama ===")
try:
    r = subprocess.run([sys.executable, "-c",
        "import requests; print('OK' if requests.get('http://localhost:11434/api/tags', timeout=3).ok else 'DOWN')"],
        capture_output=True, text=True, timeout=10)
    out.append(r.stdout.strip() or r.stderr[:200])
except Exception as e:
    out.append("check error: " + repr(e))

with open(BASE + r"\debug_result.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("done")