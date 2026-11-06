import json
segs = json.load(open("src/segs.json"))
tl = json.load(open("src/timeline.json"))
subs = []
for s, t in zip(segs, tl):
    subs.append({"s": t["start"], "e": round(t["start"] + t["dur"], 3), "text": s["text"]})
json.dump(subs, open("src/subs.json", "w"), ensure_ascii=False, indent=1)

def ts(x):
    h = int(x // 3600); m = int(x % 3600 // 60); s = int(x % 60); ms = int(round((x - int(x)) * 1000))
    if ms == 1000: s, ms = s + 1, 0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

out = []
for x in subs:
    txt = x["text"]
    if len(txt) <= 30:
        out.append((x["s"], x["e"], txt)); continue
    parts, cur = [], ""
    for ch in txt:
        cur += ch
        if ch in "，。？！；：、" and len(cur) >= 13:
            parts.append(cur); cur = ""
    if cur:
        parts.append(cur)
    total = len(txt)
    t0 = x["s"]
    for p in parts:
        d = (len(p) / total) * (x["e"] - x["s"])
        out.append((round(t0, 3), round(t0 + d, 3), p.strip()))
        t0 += d

with open("video/episode.srt", "w") as f:
    for k, (s, e, txt) in enumerate(out, 1):
        f.write(f"{k}\n{ts(s)} --> {ts(e)}\n{txt}\n\n")
json.dump([{"s": a, "e": b, "text": c} for a, b, c in out], open("src/srt.json", "w"), ensure_ascii=False)
print(len(out), "subs; last end", out[-1][1])
