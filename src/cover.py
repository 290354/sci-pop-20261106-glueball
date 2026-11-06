"""封面：1280x720，标题 + 期号 + 副标题"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E
from PIL import Image, ImageDraw, ImageFilter

img = Image.new("RGB", (E.W, E.H), E.BG)
d = ImageDraw.Draw(img, "RGBA")
E.vgrad(img, (17, 18, 24), (7, 8, 11))
E.dots(img, 1.0, n=140, bright=0.6)
cx, cy = 950, 360
for i in range(3):
    pts = []
    N = 120
    for j in range(N + 1):
        ang = j / N * 2 * 3.14159 * (1.3 + 0.35 * i) + i * 1.05
        rr = 120 * (0.6 + 0.4 * abs((j / N * 3) % 1 - 0.5) * 2)
        pts.append((cx + rr * __import__("math").cos(ang), cy + rr * 0.95 * __import__("math").sin(ang)))
    for j in range(len(pts) - 1):
        E.line(d, pts[j], pts[j + 1], [E.YEL, E.BLUE, E.mixc(E.YEL, E.RED, 0.3)][i], 4, 0.85)
E.glow(img, cx, cy, 22, E.INK, 1.0)

E.txt(d, (86, 110), "科普爆点动画周刊", E.F("sansb", 26), E.BLUE, 1.0, anchor="lm")
E.txt(d, (86, 150), "第 04 期 · 2026.11.06", E.F("sans", 20), E.DIM, 1.0, anchor="lm")
E.txt(d, (82, 340), "零个夸克", E.F("serifb", 120), E.INK, 1.0, anchor="lm")
d.rectangle([86, 412, 386, 417], fill=E.ca(E.RED, 0.9))
E.txt(d, (86, 430), "一颗粒子，一个夸克都没有", E.F("sans", 34), E.INK, 0.95)
E.txt(d, (86, 486), "却比质子还重：物质，是力打的结", E.F("sans", 30), E.YEL, 0.92)
E.txt(d, (86, 556), "BESIII · X(2370) · 胶球", E.F("sans", 24), E.BLUE, 0.9)
E.txt(d, (86, 640), "1280×720 · 30fps", E.F("sans", 18), E.DIM, 0.85)
img.save("cover.png")
print("cover ok")
