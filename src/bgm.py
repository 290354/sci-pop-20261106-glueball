"""合成配乐床：三段和声 drone + 缓慢滤波扫频，随章节微调亮度；混音时压到 -22dB 以下。"""
import subprocess, json, math
TL = json.load(open("src/timeline.json"))
TOTAL = TL[-1]["start"] + TL[-1]["dur"] + 3.0

def drone(notes, dur, f0):
    src = []
    for i, (f, a) in enumerate(notes):
        lfo = 0.04 + 0.03 * i
        src.append(f"{a:.3f}*sin(2*PI*{f}*t)*(0.6+0.4*sin(2*PI*{lfo:.3f}*t+{i}))")
    expr = "+".join(src)
    return f"aevalsrc='({expr})*0.8':s=44100:d={dur:.2f}"

# 三个段落：冷开场暗、论证段渐亮、收束段回暗
parts = [
    (0.0, 80.0, [(55, .30), (82.4, .20), (110, .12), (220, .05)]),
    (80.0, 240.0, [(55, .26), (82.4, .20), (110, .16), (164.8, .10), (329.6, .04)]),
    (240.0, TOTAL - 240.0 + 1, [(49, .32), (73.4, .22), (110, .14), (146.8, .08)]),
]
inputs, filters, labels = [], [], []
for i, (st, d, notes) in enumerate(parts):
    inputs += ["-f", "lavfi", "-i", drone(notes, d + 1, i)]
    filters.append(f"[{i}:a]lowpass=f={420 + i * 160},volume=0.55[a{i}]")
    labels.append(f"[a{i}]")
fc = ";".join(filters)
graph = fc + ";" + "".join(labels) + f"concat=n={len(parts)}:v=0:a=1,aecho=0.8:0.9:70|140:0.28|0.18,alimiter=limit=0.9[out]"
subprocess.run(["ffmpeg", "-y", "-v", "error"] + inputs + ["-filter_complex", graph, "-map", "[out]",
                "-t", f"{TOTAL:.2f}", "-ac", "2", "-ar", "44100", "audio/bgm.wav"], check=True)
print("bgm", round(TOTAL, 2))
