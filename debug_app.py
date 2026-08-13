import sys, traceback
sys.stdout.reconfigure(encoding='utf-8')

out = ""
try:
    import brain
    b = brain.JarvisBrain()
    for phrase in ["play music", "jarvis deafen my computer", "jarvis lock my computer", "jarvis skip", "jarvis go back"]:
        out += "PHRASE: " + phrase + "\n"
        events = list(b.ask_stream(phrase))
        done = [e for e in events if e["type"] == "done"][0]
        out += "  reply: " + repr(done["reply"]) + "\n"
        out += "  action: " + repr(done["action"]) + "\n\n"
except Exception:
    out = "TEST FAILED - full error:\n" + traceback.format_exc() + "\n\n"

idx = brain.SYSTEM_PROMPT.find("play_music")
snippet = brain.SYSTEM_PROMPT[idx:idx+260]
out += "PROMPT SNIPPET:\n" + repr(snippet) + "\n\n"

with open(r"C:\Users\Admin\Documents\info\projects\Jarvis\debug_result.txt", "w", encoding="utf-8") as f:
    f.write(out)
print("done")