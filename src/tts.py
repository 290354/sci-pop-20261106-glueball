import asyncio, edge_tts, json, subprocess, os

segs = json.load(open("src/segs.json"))
VOICE = os.environ.get("VOICE", "zh-CN-YunxiNeural")
GAP = 0.42

async def synth(text, out):
    if os.path.exists(out) and os.path.getsize(out) > 800:
        return
    for _ in range(3):
        try:
            await edge_tts.Communicate(text, VOICE, rate="-4%").save(out)
            return
        except Exception as e:
            print("retry", out, e)
            await asyncio.sleep(1.2)
    raise RuntimeError(out)

def dur(p):
    return float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",p]))

async def main():
    sem = asyncio.Semaphore(6)
    async def one(i, s):
        async with sem:
            await synth(s["text"], f"audio/seg_{i:02d}.mp3")
    await asyncio.gather(*[one(i, s) for i, s in enumerate(segs)])
    subprocess.run(["ffmpeg","-y","-v","error","-f","lavfi","-i","anullsrc=r=24000:cl=mono",
                    "-t",str(GAP),"-q:a","9","audio/_gap.mp3"], check=True)
    tl = []; t = 0.0
    for i, s in enumerate(segs):
        d = dur(f"audio/seg_{i:02d}.mp3")
        tl.append({"i": i, "start": round(t,3), "dur": round(d,3), "hold": s["hold"], "cap": s["cap"], "text": s["text"]})
        t += d + GAP
    json.dump(tl, open("src/timeline.json","w"), ensure_ascii=False, indent=1)
    with open("audio/_list.txt","w") as f:
        for i in range(len(segs)):
            f.write(f"file '{os.path.abspath(f'audio/seg_{i:02d}.mp3')}'\n")
            if i != len(segs)-1:
                f.write(f"file '{os.path.abspath('audio/_gap.mp3')}'\n")
    subprocess.run(["ffmpeg","-y","-v","error","-f","concat","-safe","0","-i","audio/_list.txt",
                    "-ar","44100","-ac","2","audio/voice.wav"], check=True)
    print("voice", round(dur("audio/voice.wav"),2), "segments", len(segs))

asyncio.run(main())
