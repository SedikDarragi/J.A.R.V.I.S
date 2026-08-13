import sys, traceback
sys.stdout.reconfigure(encoding='utf-8')

out = ""
try:
    import brain
    b = brain.JarvisBrain()
    events = list(b.ask_stream('Hey Jarvis.'))
    out = "TEST OK - events returned:\n" + repr(events)[:800] + "\n\n"
except Exception:
    out = "TEST FAILED - full error:\n" + traceback.format_exc() + "\n\n"

idx = brain.SYSTEM_PROMPT.find("play_music")
snippet = brain.SYSTEM_PROMPT[max(0, idx-60):idx+420]
out += "PROMPT SNIPPET (raw, as Python sees it):\n" + repr(snippet)

with open(r"C:\Users\Admin\Documents\info\projects\Jarvis\debug_result.txt", "w", encoding="utf-8") as f:
    f.write(out)
print("done")