import sys, traceback
sys.stdout.reconfigure(encoding='utf-8')

out = ""
try:
    import brain
    b = brain.JarvisBrain()
    for phrase in ["jarvis deafen my computer", "jarvis lock my computer"]:
        out += "PHRASE: " + phrase + "\n"
        events = list(b.ask_stream(phrase))
        done = [e for e in events if e["type"] == "done"][0]
        out += "  reply: " + repr(done["reply"]) + "\n"
        out += "  action: " + repr(done["action"]) + "\n\n"
except Exception:
    out = "TEST FAILED - full error:\n" + traceback.format_exc()

with open(r"C:\Users\Admin\Documents\info\projects\Jarvis\debug_result.txt", "w", encoding="utf-8") as f:
    f.write(out)
print("done")