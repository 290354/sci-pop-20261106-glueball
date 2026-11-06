# -*- coding: utf-8 -*-
"""第 04 期《零个夸克》—— 纯 PIL 决定性逐帧渲染引擎
render_at(t) -> 1280x720 PIL.Image。时间轴由 src/timeline.json 驱动（解说段落起点/时长）。
配色：底 #0E1116 / 正文 #ECE6D9 / 蓝 #58C4DD / 黄 #F4D345 / 红 #FC6255
"""
import json, math, random, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1280, 720
BG = (14, 17, 22)
INK = (236, 230, 217)
DIM = (110, 116, 126)
BLUE = (88, 196, 221)
YEL = (244, 211, 69)
RED = (252, 98, 85)
FR = 30
HERE = os.path.dirname(os.path.abspath(__file__))

SERIFB = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"
SERIF = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"
SANS = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
SANSB = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"

_fc = {}
def F(kind, size):
    key = (kind, int(size))
    if key not in _fc:
        path = {"serif": SERIF, "serifb": SERIFB, "sans": SANS, "sansb": SANSB}[kind]
        _fc[key] = ImageFont.truetype(path, int(size), index=0 if "Sans" in path else 2)
    return _fc[key]

# ---------------- 数学小工具 ----------------
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x

def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)

def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3

def ease_io(x):
    x = clamp(x)
    return 0.5 - 0.5 * math.cos(math.pi * x)

def back_out(x, s=1.6):
    x = clamp(x) - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2

def lerp(a, b, u):
    return a + (b - a) * u

def mixc(c1, c2, u):
    u = clamp(u)
    return tuple(int(lerp(c1[k], c2[k], u)) for k in range(3))

def ca(c, a):
    return (c[0], c[1], c[2], int(255 * clamp(a)))

# ---------------- 文本 ----------------
def txt(d, xy, s, font, fill, a=1.0, anchor="la", shadow=True):
    if a <= 0.01:
        return
    col = ca(fill, a)
    x, y = round(xy[0]), round(xy[1])
    if shadow:
        d.text((x + 2, y + 2), s, font=font, fill=(0, 0, 0, int(col[3] * 0.6)), anchor=anchor)
    d.text((x, y), s, font=font, fill=col, anchor=anchor)

def tc(d, x, y, s, font, fill, a=1.0, anchor="mm", shadow=True):
    txt(d, (x, y), s, font, fill, a, anchor, shadow)

def fit_font(d, s, kind, maxw, maxsize, minsize=16):
    size = maxsize
    while size > minsize:
        f = F(kind, size)
        if d.textlength(s, font=f) <= maxw:
            return f
        size -= 2
    return F(kind, minsize)

# ---------------- 时间轴 ----------------
TL = json.load(open(os.path.join(HERE, "timeline.json")))
SUBS = json.load(open(os.path.join(HERE, "subs.json")))
TOTAL = float(os.environ.get("EP_TOTAL", TL[-1]["start"] + TL[-1]["dur"] + 2.2))

STARTS = [s["start"] for s in TL]

def seg_at(t):
    """当前解说段下标 + 段内进度"""
    lo, hi = 0, len(STARTS) - 1
    if t <= STARTS[0]:
        return 0, 0.0
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if STARTS[mid] <= t:
            lo = mid
        else:
            hi = mid - 1
    s = TL[lo]
    return lo, clamp((t - s["start"]) / max(s["dur"], 0.01))

def seg_t(i):
    return TL[i]["start"]

def find(txt_part):
    for i, s in enumerate(TL):
        if txt_part in s["text"]:
            return i
    raise KeyError(txt_part)

def capstate(t):
    """返回 (屏幕文字, 透明度, 缩放) —— 取最近一个带 cap 的段落"""
    cur = None
    for s in TL:
        if s["start"] <= t:
            cur = s
        else:
            break
    if cur is None or not cur.get("cap"):
        return "", 0.0, 1.0
    u = clamp((t - cur["start"]) / 0.45)
    a_out = 1.0
    # 该段结束时淡出（到下一段前 0.25s）
    nxt = cur["start"] + cur["dur"] + 0.5
    a_out = clamp((nxt - t) / 0.25)
    return cur["cap"], smooth(u) * a_out, lerp(0.92, 1.0, ease_out(u))

# ---------------- 底层绘制 ----------------
def vgrad(img, top, bot):
    d = ImageDraw.Draw(img)
    for y in range(0, H, 2):
        d.rectangle([0, y, W, y + 1], fill=mixc(top, bot, y / H))

def dots(img, t, n=140, seed=7, bright=0.5, drift=2.0):
    rnd = random.Random(seed)
    d = ImageDraw.Draw(img, "RGBA")
    for k in range(n):
        x0, y0 = rnd.random() * W, rnd.random() * H
        r = rnd.choice([0.6, 0.8, 1.0, 1.3, 1.7])
        ph, sp = rnd.random() * 6.28, 0.5 + rnd.random() * 1.5
        a = (0.15 + 0.45 * (0.5 + 0.5 * math.sin(t * sp + ph))) * bright
        x = (x0 + t * drift) % W
        d.ellipse([x - r, y0 - r, x + r, y0 + r], fill=(236, 230, 217, int(255 * a)))

def glow(img, x, y, r, color, a=1.0, sq=1.0):
    if a <= 0.01 or r < 0.5:
        return
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for k in range(4):
        rr = r * (3.0 - k * 0.6)
        d.ellipse([x - rr, y - rr * sq, x + rr, y + rr * sq], fill=ca(color, a * (0.06 + 0.07 * k)))
    ov = ov.filter(ImageFilter.GaussianBlur(max(1, r * 0.5)))
    img.paste(ov, (0, 0), ov)
    d2 = ImageDraw.Draw(img, "RGBA")
    d2.ellipse([x - r, y - r * sq, x + r, y + r * sq], fill=ca(mixc(color, (255, 255, 255), 0.35), a))

def line(d, p0, p1, color, w=2, a=1.0):
    if a <= 0.01:
        return
    d.line([p0, p1], fill=ca(color, a), width=int(w))

def arrow(d, p0, p1, color, w=2, head=8, a=1.0):
    line(d, p0, p1, color, w, a)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    for s in (-1, 1):
        a2 = ang + math.pi - s * 0.45
        line(d, p1, (p1[0] + head * math.cos(a2), p1[1] + head * math.sin(a2)), color, w, a)

def hl(img, x, y, w, h, color=None):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.rectangle([x, y, x + w, y + h], fill=(6, 8, 12, 150))
    img.paste(ov, (0, 0), ov)

def dashed(d, p0, p1, color, a=0.5, w=1, dash=7, gap=6):
    x0, y0 = p0; x1, y1 = p1
    L = math.hypot(x1 - x0, y1 - y0)
    if L < 1:
        return
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    s = 0.0
    while s < L:
        e = min(s + dash, L)
        line(d, (x0 + ux * s, y0 + uy * s), (x0 + ux * e, y0 + uy * e), color, w, a)
        s = e + gap

def ribbon(d, pts, color, w, a):
    """沿点的粗线（用圆点填充，避免 PIL 粗线断裂）"""
    if len(pts) < 2:
        return
    for i in range(len(pts) - 1):
        line(d, pts[i], pts[i + 1], color, w, a)
    for p in pts[::3]:
        r = w / 2
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=ca(color, a))

# ---------------- 公共装饰 ----------------
CHAP = [
    (0.0, "冷开场"),
    (24.0, "第一章 · 力也会粘自己"),
    (80.0, "第二章 · 能量称重"),
    (148.0, "第三章 · 三样证据"),
    (240.0, "第四章 · 边界与推论"),
    (306.0, "回到零个夸克"),
]

def chapter_at(t):
    lab = CHAP[0][1]
    for t0, name in CHAP:
        if t >= t0:
            lab = name
    return lab

def hud(img, d, t, idx=None):
    a = smooth((t - 0.6) / 1.2) * clamp((TOTAL - t) / 2.0)
    if a <= 0.02:
        return
    tc(d, 64, 44, "科普爆点动画周刊 · 第 04 期", F("sans", 17), DIM, a * 0.9, anchor="lm")
    lab = chapter_at(t)
    d.ellipse([1010, 44, 1017, 51], fill=ca(mixc(RED, YEL, 0.0), a * 0.85))
    tc(d, 1024, 44, lab, F("sans", 16), DIM, a * 0.85, anchor="lm")
    # 底部细进度条
    d.rectangle([0, H - 3, W * clamp(t / TOTAL), H], fill=ca(mixc(BLUE, YEL, clamp(t / TOTAL)), 0.30 * a))

def caption(img, d, t):
    s, a, sc = capstate(t)
    if not s or a <= 0.02:
        return
    f = F("serifb", 52)
    wd = d.textlength(s, font=f)
    if wd > 1080:
        f = F("serifb", int(52 * 1080 / wd))
        wd = d.textlength(s, font=f)
    y = 196
    # 左侧竖线
    d.rectangle([W / 2 - wd / 2 - 26, y - 26, W / 2 - wd / 2 - 21, y + 26], fill=ca(RED, a * 0.9))
    tc(d, W / 2 + 4, y, s, f, INK, a, shadow=True)

def subtitle(img, d, t):
    cur = None
    for s in SUBS:
        if s["s"] <= t <= s["e"] + 0.05:
            cur = s
            break
    if cur is None:
        # 段间间隔里保持上一条 0.25s 余像，减少闪烁
        for s in SUBS:
            if s["e"] < t <= s["e"] + 0.25:
                cur = s
    if cur is None:
        return
    s = cur["text"]
    a = clamp((t - cur["s"]) / 0.12) * clamp((cur["e"] + 0.12 - t) / 0.12)
    if a <= 0.02:
        return
    f = F("sans", 27)
    while d.textlength(s, font=f) > 1120 and f.size > 18:
        f = F("sans", f.size - 1)
    wd = d.textlength(s, font=f)
    y = 664
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(ov)
    dd.rounded_rectangle([W / 2 - wd / 2 - 20, y - 24, W / 2 + wd / 2 + 20, y + 24], radius=8,
                         fill=(8, 10, 14, int(190 * a)))
    img.paste(ov, (0, 0), ov)
    tc(d, W / 2, y, s, f, INK, a * 0.97, shadow=False)

# ---------------- 角色：胶子 / 夸克 ----------------
def particle(d, x, y, r, color, a=1.0, ring=True, fill_a=0.95):
    if a <= 0.01:
        return
    d.ellipse([x - r, y - r, x + r, y + r], fill=ca(mixc(color, BG, 0.25), a * fill_a))
    if ring:
        d.ellipse([x - r, y - r, x + r, y + r], outline=ca(mixc(color, INK, 0.4), a), width=2)
        d.ellipse([x - r * 0.42, y - r * 0.42, x + r * 0.42, y + r * 0.42], fill=ca(mixc(color, (255, 255, 255), 0.5), a * 0.8))

def spring(d, p0, p1, color, a=1.0, n=7, amp=6, w=2, phase=0.0, sag=0.0):
    """把两点连成弹簧/波动绳"""
    if a <= 0.01:
        return
    x0, y0 = p0; x1, y1 = p1
    L = math.hypot(x1 - x0, y1 - y0)
    if L < 1:
        return
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    nx, ny = -uy, ux
    pts = []
    steps = n * 6
    for k in range(steps + 1):
        u = k / steps
        s_ = math.sin(u * n * 2 * math.pi + phase)
        off = amp * s_ * math.sin(math.pi * u) + sag * math.sin(math.pi * u)
        pts.append((x0 + ux * L * u + nx * off, y0 + uy * L * u + ny * off))
    for k in range(len(pts) - 1):
        line(d, pts[k], pts[k + 1], color, w, a)

def gluon_loop(d, cx, cy, R, k, color, a=1.0, t=0.0, w=2):
    """画一条扭曲的胶子线：k 个结"""
    pts = []
    N = 160
    for i in range(N + 1):
        u = i / N
        ang = u * 2 * math.pi + t * 0.6
        r = R + 5 * math.sin(u * k * 2 * math.pi * 2 + t * 2.0)
        pts.append((cx + r * math.cos(ang), cy + r * 0.86 * math.sin(ang)))
    for i in range(len(pts) - 1):
        line(d, pts[i], pts[i + 1], color, w, a)

# ---------------- 场景 ----------------
def sc_open1(img, d, t, u):
    """0: 一团看不见的东西把光点夹住"""
    vgrad(img, (13, 16, 21), (8, 9, 13))
    dots(img, t, n=90, bright=0.35)
    cx, cy = W / 2, 330
    a = smooth(u / 0.4)
    # 两团"力"从左右压过来
    for sgn in (-1, 1):
        px = cx + sgn * lerp(330, 120, ease_out((u - 0.05) / 0.55))
        glow(img, px, cy, 26, BLUE if sgn < 0 else YEL, a * 0.55, 1.0)
    # 光点来回弹
    bx = cx + 42 * math.sin(t * 2.6) * (1 - 0.35 * clamp(u))
    glow(img, bx, cy + 8 * math.sin(t * 3.3), 15, INK, a, 1.0)
    if u > 0.45:
        a2 = smooth((u - 0.45) / 0.3)
        tc(d, cx, cy + 96, "两团看不见的力，把它夹住", F("sans", 26), DIM, a2, anchor="mm")

def sc_open2(img, d, t, u):
    """1: 拉远，整屏都是同款小球"""
    vgrad(img, (13, 16, 21), (8, 9, 13))
    cx, cy = W / 2, 330
    k = ease_io((u - 0.02) / 0.5)
    n = 5 + int(52 * k)
    rnd = random.Random(23)
    for i in range(n):
        ang = rnd.random() * 6.28
        dist = rnd.random() ** 0.6 * lerp(70, 760, k)
        x = cx + math.cos(ang) * dist * 1.35
        y = cy + math.sin(ang) * dist * 0.8
        if not (-40 < x < W + 40 and -40 < y < H + 40):
            continue
        s = 0.5 + 0.5 * math.sin(t * 1.8 + i)
        a = smooth((u - 0.02 - (i / max(n, 1)) * 0.25) / 0.3)
        particle(d, x, y, 9 + 5 * s * 0.4, RED if i % 7 == 0 else (BLUE if i % 3 == 0 else YEL), a * 0.75)
    # 中央那颗最大
    glow(img, cx, cy, 16 + 3 * math.sin(t * 3), INK, 1.0)

def sc_you(img, d, t, u):
    """2: 一个人形轮廓由万点组成"""
    vgrad(img, (15, 14, 18), (8, 9, 13))
    dots(img, t, n=100, bright=0.3)
    cx, cy = W / 2, 330
    rnd = random.Random(5)
    # 用椭圆+矩形近似肩胸轮廓
    N = 460
    for i in range(N):
        ang = rnd.random() * 2 * math.pi
        rr = math.sqrt(rnd.random())
        x = cx + math.cos(ang) * rr * 118
        y = cy + 40 + math.sin(ang) * rr * 150
        if y < cy - 110 and abs(x - cx) > 55:
            continue
        a = smooth((u - i / N * 0.55) / 0.25)
        particle(d, x, y, 2.6 + 1.6 * rnd.random(), BLUE if rnd.random() < 0.7 else YEL, a * 0.8, ring=False)
    tc(d, W / 2, cy + 240, "你 · 99% 是力", F("sans", 26), DIM, smooth((u - 0.5) / 0.3))

def sc_proton(img, d, t, u):
    """3: 质子剖开，三夸克被弹簧锁住；拉不动"""
    vgrad(img, (14, 17, 22), (8, 9, 13))
    cx, cy = W / 2, 360
    pp = smooth((u - 0.05) / 0.25)
    tc(d, cx, 210, "质子：三个夸克，一根拉不断的绳子", F("sansb", 30), INK, pp * smooth((u - 0.08) / 0.3), anchor="mm")
    R = 150 * back_out((u - 0.02) / 0.35)
    if R > 2:
        d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=ca(BLUE, pp * 0.35), width=2)
        # 内部胶子场：一堆乱飞的短线
        rnd = random.Random(9)
        for i in range(46):
            ang = rnd.random() * 6.28 + t * (0.3 + rnd.random() * 0.8)
            rr = R * (0.15 + 0.75 * rnd.random())
            x = cx + math.cos(ang) * rr
            y = cy + math.sin(ang) * rr * 0.9
            ln = 8 + 12 * rnd.random()
            d.line([(x, y), (x + ln * math.cos(ang + 1.4), y + ln * math.sin(ang + 1.4))],
                   fill=ca(YEL, pp * 0.35), width=2)
    # 三个夸克，第三个被往右拉
    pull = ease_io((u - 0.35) / 0.55) * 150
    base = [(-72, -60), (58, -72), (18, 66)]
    pos = []
    for i, (bx, by) in enumerate(base):
        x, y = cx + bx, cy + by
        if i == 2:
            x += pull
        pos.append((x, y))
    for i in range(3):
        for j in range(i + 1, 3):
            spring(d, pos[i], pos[j], YEL, pp * 0.85, n=6, amp=5, w=2, phase=t * 6 + i + j)
    for i, (x, y) in enumerate(pos):
        particle(d, x, y, 15, RED if i == 2 else BLUE, pp, ring=True)
    tc(d, pos[2][0] + 30, pos[2][1] - 34, "夸克", F("sans", 20), RED, pp * smooth((u - 0.3) / 0.3), anchor="lm")

def sc_snap(img, d, t, u):
    """4: 拉断 → 长出新夸克"""
    vgrad(img, (20, 14, 18), (8, 9, 13))
    cx, cy = W / 2, 340
    pp = smooth((u - 0.02) / 0.2)
    L = lerp(90, 250, ease_io((u - 0.05) / 0.42))
    snap = clamp((u - 0.52) / 0.12)
    a0 = (cx - L, cy - 40); a1 = (cx + L, cy + 20)
    if snap < 0.02:
        spring(d, a0, a1, YEL, pp, n=8, amp=9, w=3, phase=t * 8)
        particle(d, a0[0], a0[1], 15, BLUE, pp)
        particle(d, a1[0], a1[1], 15, RED, pp)
    else:
        k = ease_out(snap)
        for sgn in (-1, 1):
            e = (cx + sgn * 40, cy - 10 + sgn * 6)
            a = (1 - k) * pp
            spring(d, a0 if sgn < 0 else a1, e, YEL, a, n=4, amp=8, w=3, phase=t * 8)
            particle(d, a0[0], a0[1], 15, BLUE, a)
            particle(d, a1[0], a1[1], 15, RED, a)
        # 新长出的一对，从中间飞开
        for sgn, col in ((1, BLUE), (-1, RED)):
            px = lerp(cx, cx + sgn * 130, k)
            py = cy + sgn * 26 * k
            particle(d, px, py, 15, col, smooth((snap - 0.15) / 0.3))
            glow(img, px, py, 18, col, 0.9 * smooth((snap - 0.15) / 0.3))
        if 0.1 < snap < 0.5:
            glow(img, cx, cy - 10, 40 * (1 - snap), INK, (1 - snap) * 0.8)

def sc_more(img, d, t, u):
    """5: 越撕越多"""
    vgrad(img, (16, 15, 19), (8, 9, 13))
    cx, cy = W / 2, 330
    pp = smooth((u - 0.02) / 0.25)
    rnd = random.Random(31)
    pts = []
    n = 3 + int(20 * clamp((u - 0.1) / 0.6))
    for i in range(n):
        ang = rnd.random() * 6.28
        dist = 40 + rnd.random() * 230
        x = cx + math.cos(ang) * dist * 1.4
        y = cy + math.sin(ang) * dist * 0.8
        pts.append((x, y, BLUE if i % 2 else RED))
    for i in range(len(pts)):
        for j in range(i + 1, min(len(pts), i + 3)):
            if (i + j) % 3 == 0:
                spring(d, pts[i][:2], pts[j][:2], YEL, pp * 0.35, n=3, amp=3, w=1, phase=t * 5 + i)
    for i, (x, y, c) in enumerate(pts):
        a = smooth((u - 0.08 - i / max(n, 1) * 0.3) / 0.2)
        particle(d, x, y, 11, c, a * pp)
    tc(d, cx, cy + 240, "越撕越多 · 禁闭", F("sansb", 28), RED, pp * smooth((u - 0.55) / 0.3))

def sc_gluon_sep(img, d, t, u):
    """6: 胶子自己单独拿出来 → 只能存在一瞬"""
    vgrad(img, (14, 17, 22), (8, 9, 13))
    cx, cy = W / 2, 340
    pp = smooth((u - 0.03) / 0.25)
    # 背景：质子残影
    d.ellipse([cx - 130, cy - 130, cx + 130, cy + 130], outline=ca(BLUE, pp * 0.12), width=1)
    for i in range(10):
        ang = i * 0.63 + t * 0.4
        x, y = cx + math.cos(ang) * 100, cy + math.sin(ang) * 100
        particle(d, x, y, 6, BLUE, pp * 0.25, ring=False)
    # 胶子被"拎"出来
    k = ease_io((u - 0.15) / 0.65)
    gx, gy = cx + 20, cy - lerp(0, 90, k)
    life = 1 - clamp((u - 0.55) / 0.35)
    gluon_loop(d, gx, gy, 26, 2, YEL, pp * max(life, 0) ** 0.7, t, 3)
    tc(d, gx, gy - 62, "胶子", F("sans", 22), YEL, pp * life, anchor="mm")
    if u > 0.6:
        tc(d, cx, cy + 200, "离开就消失", F("sansb", 30), DIM, smooth((u - 0.62) / 0.3))

def sc_three_colors(img, d, t, u):
    """7: 三种色 + 三种反色 → 胶子吃自己"""
    vgrad(img, (14, 17, 22), (8, 9, 13))
    cx, cy = W / 2, 250
    pp = smooth((u - 0.03) / 0.25)
    cols = [RED, BLUE, YEL]
    names = ["红", "绿", "蓝"]
    for i in range(3):
        ang = -math.pi / 2 + i * 2 * math.pi / 3 + t * 0.5
        x, y = cx + math.cos(ang) * 105, cy + math.sin(ang) * 100
        particle(d, x, y, 20, cols[i], pp * smooth((u - 0.05 - i * 0.1) / 0.25))
        tc(d, x, y + 40, names[i] + "色", F("sans", 18), cols[i], pp * 0.9, anchor="mm")
    # 下方：胶子带色荷 → 自己和自己连
    gy = 520
    a2 = smooth((u - 0.45) / 0.3)
    gluon_loop(d, cx - 170, gy, 34, 2, YEL, pp * a2, t, 3)
    gluon_loop(d, cx + 170, gy, 34, 2, YEL, pp * a2, t + 1, 3)
    spring(d, (cx - 134, gy), (cx + 134, gy), YEL, pp * a2 * 0.9, n=7, amp=14, w=3, phase=t * 6)
    tc(d, cx, gy + 74, "胶子吃自己", F("serifb", 34), YEL, pp * a2, anchor="mm")

def sc_knot(img, d, t, u):
    """8: 力打结 → 成球"""
    vgrad(img, (16, 14, 18), (8, 9, 13))
    dots(img, t, n=70, bright=0.3)
    cx, cy = W / 2, 340
    pp = smooth((u - 0.02) / 0.2)
    k = ease_io((u - 0.1) / 0.55)
    R = lerp(150, 70, k)
    # 两条胶子线互相缠绕，逐步收紧
    for j in range(2):
        pts = []
        N = 150
        for i in range(N + 1):
            ang = i / N * 2 * math.pi * (2 + j) + t * (0.8 + 0.4 * j) + j * 1.2
            rr = R * (1 + 0.28 * math.sin(i / N * 2 * math.pi * 3 + t))
            pts.append((cx + rr * math.cos(ang), cy + rr * 0.9 * math.sin(ang)))
        for i in range(len(pts) - 1):
            line(d, pts[i], pts[i + 1], mixc(YEL, BLUE, j * 0.8), 3, pp * (0.55 + 0.45 * k))
    core = smooth((u - 0.5) / 0.3)
    glow(img, cx, cy, 14 + 16 * core, mixc(YEL, INK, 0.4), pp * (0.4 + 0.6 * core))
    if core > 0:
        d.ellipse([cx - 46, cy - 46, cx + 46, cy + 46], outline=ca(INK, core * 0.8), width=2)
        tc(d, cx, cy + 118, "胶球", F("serifb", 46), INK, core, anchor="mm")

def sc_glueball_label(img, d, t, u):
    """9: 胶球命名卡，旁挂 2.37 GeV 预告"""
    vgrad(img, (16, 14, 18), (8, 9, 13))
    cx, cy = 420, 350
    pp = smooth((u - 0.02) / 0.2)
    R = 92
    for i in range(3):
        pts = []
        N = 110
        for k in range(N + 1):
            ang = k / N * 2 * math.pi * (1.5 + 0.5 * i) + t * (0.7 + 0.3 * i) + i
            rr = R * (0.55 + 0.45 * abs(math.sin(k / N * 3 * math.pi + t * 0.6)))
            pts.append((cx + rr * math.cos(ang), cy + rr * 0.92 * math.sin(ang)))
        for k in range(len(pts) - 1):
            line(d, pts[k], pts[k + 1], [YEL, BLUE, mixc(YEL, RED, 0.3)][i], 3, pp * 0.8)
    glow(img, cx, cy, 18, INK, pp)
    tc(d, cx, cy + 150, "胶球 glueball", F("serifb", 40), INK, pp, anchor="mm")
    a2 = smooth((u - 0.4) / 0.3)
    tc(d, 860, 300, "2 个胶子", F("sans", 30), YEL, a2, anchor="mm")
    tc(d, 860, 348, "+ 1 个胶子", F("sans", 30), BLUE, a2, anchor="mm")
    tc(d, 860, 404, "= 一颗球", F("sansb", 34), INK, smooth((u - 0.6) / 0.3), anchor="mm")

def sc_forty_years(img, d, t, u):
    """10: 时间轴 1980s → 今天"""
    vgrad(img, (14, 16, 22), (8, 9, 13))
    y = 400
    pp = smooth((u - 0.03) / 0.25)
    x0, x1 = 160, 1120
    k = ease_io((u - 0.1) / 0.7)
    line(d, (x0, y), (lerp(x0, x1, k), y), BLUE, 2, pp * 0.7)
    for i, (fr, lab, col) in enumerate([(0.0, "1980s 理论预言", DIM), (0.55, "2009 首次看见", BLUE), (0.9, "2026 认出来", YEL)]):
        a = smooth((k - fr) / 0.06) * pp
        x = x0 + (x1 - x0) * fr
        d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=ca(col, a))
        tc(d, x, y - 34, lab, F("sans", 22), col, a, anchor="mm")
    tc(d, W / 2, 250, "四十年", F("serifb", 92), INK, pp * smooth((u - 0.2) / 0.3), anchor="mm")
    tc(d, W / 2, 560, "五代人 · 两代加速器 · 三代探测器", F("sans", 24), DIM, pp * smooth((u - 0.55) / 0.3), anchor="mm")

def sc_energy_mass(img, d, t, u):
    """11: 胶子在球里跑，能量读数变质量"""
    vgrad(img, (18, 15, 17), (8, 9, 13))
    cx, cy = 470, 340
    pp = smooth((u - 0.02) / 0.2)
    R = 120
    d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=ca(INK, pp * 0.5), width=2)
    # 内部弹跳的光点
    rnd = random.Random(77)
    for i in range(7):
        rx, ry = rnd.uniform(0.3, 0.85), rnd.uniform(0.3, 0.85)
        sp = 0.7 + rnd.random()
        fx = cx + R * rx * math.sin(t * sp + i)
        fy = cy + R * ry * math.cos(t * sp * 1.3 + i * 2)
        glow(img, fx, fy, 7, YEL, pp, 1.0)
    # 读数
    a2 = smooth((u - 0.25) / 0.3)
    v = lerp(0.0, 2.37, ease_out((u - 0.3) / 0.6))
    tc(d, 880, 280, "质量", F("sans", 24), DIM, a2, anchor="mm")
    tc(d, 880, 344, f"{v:.2f}", F("serifb", 76), YEL if v > 2.3 else INK, a2, anchor="mm")
    tc(d, 880, 404, "GeV / c²", F("sans", 22), DIM, a2, anchor="mm")
    if u > 0.55:
        a3 = smooth((u - 0.55) / 0.25)
        tc(d, 880, 210, "胶子：静止质量 0", F("sans", 22), BLUE, a3, anchor="mm")

def sc_emc2(img, d, t, u):
    """12: E = mc²"""
    vgrad(img, (14, 16, 22), (8, 9, 13))
    pp = smooth((u - 0.05) / 0.3)
    tc(d, W / 2 - 130, 320, "E", F("serifb", 76), YEL, pp, anchor="mm")
    tc(d, W / 2 - 70, 320, "=", F("serifb", 64), INK, pp, anchor="mm")
    tc(d, W / 2 - 10, 320, "m", F("serifb", 76), BLUE, pp, anchor="mm")
    tc(d, W / 2 + 50, 320, "c", F("serifb", 62), RED, pp, anchor="mm")
    tc(d, W / 2 + 80, 296, "2", F("serifb", 34), RED, pp, anchor="mm")
    a2 = smooth((u - 0.4) / 0.3)
    tc(d, W / 2, 430, "能量一挤压，就成了质量", F("sans", 30), INK, a2, anchor="mm")
    # 虚线框住公式
    if a2 > 0:
        dashed(d, (W / 2 - 230, 250), (W / 2 + 160, 250), INK, a2 * 0.25, 1, 6, 6)
        dashed(d, (W / 2 - 230, 390), (W / 2 + 160, 390), INK, a2 * 0.25, 1, 6, 6)

def sc_heavier(img, d, t, u):
    """13: 胶球 vs 质子质量对比"""
    vgrad(img, (14, 16, 22), (8, 9, 13))
    pp = smooth((u - 0.02) / 0.25)
    # 两条水平条
    k = ease_out((u - 0.1) / 0.55)
    x0 = 250
    bars = [("胶球 2.37 GeV", 2.37, YEL, 230), ("质子 0.938 GeV", 0.94, INK, 320)]
    for i, (lab, v, col, y) in enumerate(bars):
        a = pp * smooth((u - 0.06 - i * 0.12) / 0.25)
        tc(d, x0 - 30, y, lab, F("sans", 25), col, a, anchor="rm")
        wmax = 620
        w = wmax * (v / 2.37) * k
        d.rectangle([x0, y - 16, x0 + w, y + 16], fill=ca(col, a * 0.85))
    a2 = smooth((u - 0.55) / 0.3)
    tc(d, W / 2, 460, "什么都没装，却比质子更重", F("sans", 28), DIM, a2, anchor="mm")

def sc_quark_1pct(img, d, t, u):
    """14: 质子质量拆账：1% vs 99%"""
    vgrad(img, (16, 15, 19), (8, 9, 13))
    pp = smooth((u - 0.02) / 0.25)
    x0, x1, y = 190, 1090, 330
    Wd = x1 - x0
    k = ease_io((u - 0.12) / 0.55)
    a = pp * smooth((u - 0.05) / 0.25)
    d.rounded_rectangle([x0, y - 34, x1, y + 34], radius=8, outline=ca(DIM, a * 0.7), width=2)
    # 99% 部分从右往左填
    w99 = Wd * 0.99 * k
    d.rectangle([x1 - w99, y - 32, x1, y + 32], fill=ca(YEL, a * 0.85))
    w1 = Wd * 0.01 * k
    d.rectangle([x0, y - 32, x0 + max(w1, 1.5), y + 32], fill=ca(RED, a))
    tc(d, x0 + 30, y + 74, "夸克自身 1%", F("sansb", 24), RED, smooth((u - 0.2) / 0.3), anchor="lm")
    tc(d, x1 - 40, y + 74, "胶子场能量 99%", F("sansb", 26), YEL, smooth((u - 0.35) / 0.3), anchor="rm")
    if u > 0.55:
        a3 = smooth((u - 0.55) / 0.3)
        tc(d, W / 2, 470, "质子的质量账本", F("serifb", 40), INK, a3, anchor="mm")

def sc_mass_originates(img, d, t, u):
    """15: 99% 铺满屏幕，人形由能量团组成"""
    vgrad(img, (22, 19, 12), (10, 10, 12))
    cx, cy = W / 2, 330
    pp = smooth((u - 0.03) / 0.3)
    rnd = random.Random(41)
    # 一大团翻腾的能量组成人形
    for i in range(240):
        ang = rnd.random() * 6.28
        rr = math.sqrt(rnd.random())
        x = cx + math.cos(ang + t * 0.5) * rr * 130
        y = cy + 40 + math.sin(ang + t * 0.7) * rr * 165
        if y < cy - 120 and abs(x - cx) > 52:
            continue
        a = pp * (0.18 + 0.5 * rnd.random())
        d.line([(x, y), (x + 10 * math.cos(t * 2 + i), y + 10 * math.sin(t * 2.3 + i))], fill=ca(YEL, a), width=2)
    tc(d, W / 2, 130, "99%", F("serifb", 110), YEL, pp, anchor="mm")
    tc(d, W / 2, 560, "你的体重，来自力", F("sansb", 30), INK, pp * smooth((u - 0.3) / 0.3), anchor="mm")

def sc_glue_not_water(img, d, t, u):
    """16: 胶水比喻的更正：不是粘出来，是凝出来"""
    vgrad(img, (15, 16, 20), (8, 9, 13))
    pp = smooth((u - 0.03) / 0.25)
    cx = W / 2
    a1 = smooth((u - 0.08) / 0.25) * clamp((0.75 - u) / 0.2)
    a2 = smooth((u - 0.4) / 0.3)
    tc(d, cx, 300, "物质 + 胶水", F("sans", 42), DIM, a1, anchor="mm")
    tc(d, cx, 300, "力量本身", F("serifb", 66), YEL, a2, anchor="mm")
    tc(d, cx, 400, "是力自己，凝成了物质", F("sans", 30), INK, a2, anchor="mm")

def sc_collider(img, d, t, u):
    """17: 对撞机：e+e- 相撞，碎片飞溅"""
    vgrad(img, (12, 14, 20), (8, 9, 13))
    cx, cy = W / 2, 320
    pp = smooth((u - 0.02) / 0.2)
    # 环形加速器俯视
    d.ellipse([cx - 330, cy - 170, cx + 330, cy + 170], outline=ca(BLUE, pp * 0.22), width=2)
    for i in range(26):
        ang = i / 26 * 6.28 + t * 0.25
        d.ellipse([cx + 330 * math.cos(ang) - 2, cy + 170 * math.sin(ang) - 2,
                   cx + 330 * math.cos(ang) + 2, cy + 170 * math.sin(ang) + 2], fill=ca(BLUE, pp * 0.3))
    hit = clamp((u - 0.18) / 0.08)
    # 两束相向运动的光点
    if hit < 0.98:
        for sgn in (-1, 1):
            x = cx + sgn * lerp(300, 8, ease_io(clamp(u / 0.26)))
            glow(img, x, cy, 9, BLUE if sgn < 0 else RED, pp * (1 - hit * 0.6), 1.0)
    if hit > 0:
        k = (u - 0.18) / 0.7
        rnd = random.Random(13)
        for i in range(90):
            ang = rnd.random() * 6.28
            sp = 0.4 + rnd.random()
            dist = (260 * sp) * ease_out(k)
            x = cx + math.cos(ang) * dist
            y = cy + math.sin(ang) * dist * 0.7
            a = pp * clamp(1.2 - k * 1.1) * (0.5 + 0.5 * rnd.random())
            particle(d, x, y, 3 + 4 * rnd.random(), BLUE if i % 3 else RED, a, ring=False)
        glow(img, cx, cy, 30 * (1 - k * 0.7) + 6, INK, pp * clamp(1.5 - k))

def sc_2009(img, d, t, u):
    """18: 2009 碎片里一个可疑亮点"""
    vgrad(img, (12, 14, 20), (8, 9, 13))
    cx, cy = W / 2, 330
    pp = smooth((u - 0.02) / 0.25)
    rnd = random.Random(101)
    for i in range(220):
        ang = rnd.random() * 6.28
        dist = 40 + rnd.random() ** 0.7 * 430
        x = cx + math.cos(ang) * dist * 1.25
        y = cy + math.sin(ang) * dist * 0.78
        a = pp * (0.10 + 0.30 * rnd.random())
        particle(d, x, y, 2 + 2.5 * rnd.random(), BLUE if rnd.random() < 0.6 else DIM, a, ring=False)
    hi = smooth((u - 0.35) / 0.25)
    hx, hy = cx + 120, cy - 60
    particle(d, hx, hy, 7, YEL, pp * (0.35 + 0.65 * hi), ring=False)
    if hi > 0:
        glow(img, hx, hy, 11 + 3 * math.sin(t * 4), YEL, hi)
        # 圈注
        r = 46 * back_out((u - 0.38) / 0.3)
        if r > 2:
            d.ellipse([hx - r, hy - r * 0.86, hx + r, hy + r * 0.86], outline=ca(YEL, hi), width=3)
        tc(d, hx + 70, hy - 16, "X(2370)", F("serifb", 34), YEL, smooth((u - 0.55) / 0.25), anchor="lm")
    tc(d, 200, 560, "2009 · 北京正负电子对撞机", F("sans", 20), DIM, pp * 0.85, anchor="lm")

def sc_noise(img, d, t, u):
    """19: 本底淹没信号"""
    vgrad(img, (13, 15, 19), (8, 9, 13))
    cx, cy = W / 2, 330
    pp = smooth((u - 0.02) / 0.25)
    rnd = random.Random(303)
    n = int(140 + 320 * clamp((u - 0.05) / 0.5))
    for i in range(n):
        ang = rnd.random() * 6.28
        dist = rnd.random() ** 0.55 * 560
        x = cx + math.cos(ang) * dist
        y = cy + math.sin(ang) * dist * 0.68
        a = pp * (0.06 + 0.22 * rnd.random())
        d.point((x, y), fill=ca(BLUE if rnd.random() < 0.5 else INK, a))
    hi = 1 - smooth((u - 0.25) / 0.5) * 0.72
    glow(img, cx + 120, cy - 60, 10, YEL, pp * hi * 0.9)
    a2 = smooth((u - 0.3) / 0.3)
    tc(d, W / 2, 560, "一半以上，是干扰", F("serifb", 40), RED, a2, anchor="mm")
    a3 = smooth((u - 0.62) / 0.3)
    tc(d, 1120, 90, "本底 ≈ 50%+", F("sans", 20), DIM, a3, anchor="rm")

def sc_three_checks(img, d, t, u):
    """20: 三样证据 关卡"""
    vgrad(img, (14, 16, 22), (8, 9, 13))
    pp = smooth((u - 0.02) / 0.25)
    cx, cy = W / 2, 320
    # 中心粒子
    glow(img, cx, cy, 26, INK, pp)
    items = [("一 · 质量", 30, BLUE), ("二 · 自旋宇称", 150, YEL), ("三 · 味单态", 270, RED)]
    for i, (lab, ang_d, col) in enumerate(items):
        ang = math.radians(ang_d)
        k = ease_out((u - 0.1 - i * 0.18) / 0.4)
        x = cx + math.cos(ang) * lerp(60, 300, k)
        y = cy + math.sin(ang) * lerp(20, 150, k)
        a = pp * smooth((u - 0.08 - i * 0.18) / 0.25)
        dashed(d, (cx, cy), (x, y), col, a * 0.35, 1, 6, 6)
        particle(d, x, y, 10, col, a, ring=False)
        tc(d, x, y - 12 + (44 if ang_d == 30 else -40 * (1 if ang_d < 90 else -1)), lab, F("sansb", 24), col, a, anchor="mm")

def sc_check1_mass(img, d, t, u):
    """21: 质量：格点计算曲线 vs 实验值"""
    vgrad(img, (14, 16, 22), (8, 9, 13))
    pp = smooth((u - 0.02) / 0.25)
    ox, oy = 300, 520
    a2 = smooth((u - 0.1) / 0.3)
    # 坐标轴
    line(d, (ox, oy), (ox, oy - 320), DIM, 2, a2 * 0.7)
    line(d, (ox, oy), (ox + 720, oy), DIM, 2, a2 * 0.7)
    tc(d, ox - 16, oy - 336, "质量", F("sans", 18), DIM, a2, anchor="mm")
    tc(d, ox + 730, oy + 24, "格点计算", F("sans", 18), DIM, a2, anchor="rm")
    # 曲线
    pts = []
    for i in range(120):
        x = ox + 40 + i * 5.6
        y = oy - 120 - 150 * math.exp(-((i - 70) / 34) ** 2)
        pts.append((x, y))
    k = clamp((u - 0.15) / 0.45)
    m = int(len(pts) * ease_out(k))
    for i in range(max(m - 1, 0)):
        line(d, pts[i], pts[i + 1], BLUE, 3, pp)
    if m > 10:
        px, py = pts[m - 1]
        glow(img, px, py, 7, BLUE, pp)
    a3 = smooth((u - 0.5) / 0.25)
    if a3 > 0:
        X, Y = ox + 40 + 70 * 5.6, oy - 270
        d.line([(X, oy), (X, Y)], fill=ca(YEL, a3 * 0.8), width=2)
        glow(img, X, Y, 10, YEL, a3)
        tc(d, X + 20, Y - 20, "实测 2.37 GeV", F("sansb", 26), YEL, a3, anchor="lm")
        tc(d, X + 20, Y + 14, "与计算几乎重合", F("sans", 20), DIM, a3, anchor="lm")

def sc_check2_spin(img, d, t, u):
    """22: 自旋宇称：箭头转，照镜子翻面"""
    vgrad(img, (15, 15, 20), (8, 9, 13))
    pp = smooth((u - 0.02) / 0.25)
    cx, cy = 430, 330
    # 左边的球 + 箭头
    ang = t * 1.2
    glow(img, cx, cy, 26, INK, pp)
    ax, ay = cx + 90 * math.cos(ang), cy + 26 * math.sin(ang)
    arrow(d, (cx, cy), (ax, ay), YEL, 3, 10, pp)
    tc(d, cx, cy + 100, "自旋 0", F("sans", 24), INK, pp, anchor="mm")
    # 右侧：镜面
    a2 = smooth((u - 0.35) / 0.3)
    mx = 900
    line(d, (mx, 120), (mx, 560), BLUE, 1, a2 * 0.4)
    for yy in range(130, 560, 16):
        line(d, (mx - 5, yy), (mx, yy + 8), BLUE, 1, a2 * 0.3)
    cx2 = mx + 170
    glow(img, cx2, cy, 26 * a2, INK, a2)
    ax2, ay2 = cx2 - 90 * math.cos(ang), cy + 26 * math.sin(ang)
    arrow(d, (cx2, cy), (ax2, ay2), RED, 3, 10, a2)
    tc(d, cx2, cy + 100, "照镜子：翻面", F("sansb", 24), RED, a2 * smooth((u - 0.5) / 0.25), anchor="mm")
    tc(d, (mx + cx2) / 2, 620, "赝标量", F("serifb", 32), YEL, a2 * smooth((u - 0.62) / 0.25), anchor="mm")

def sc_check3_flavor(img, d, t, u):
    """23: 味单态：筛掉带味道的，只留下无色"""
    vgrad(img, (14, 16, 22), (8, 9, 13))
    pp = smooth((u - 0.02) / 0.25)
    cx, cy = W / 2, 320
    rnd = random.Random(57)
    cols = {"u": BLUE, "d": RED, "s": YEL}
    # 一堆带味道的粒子，逐渐被"筛"到两侧淡出
    filt = ease_io((u - 0.2) / 0.5)
    for i in range(60):
        key = ["u", "d", "s"][i % 3]
        ang = rnd.random() * 6.28
        dist = 40 + rnd.random() * 250
        x0 = cx + math.cos(ang) * dist * 1.3
        y0 = cy + math.sin(ang) * dist * 0.7
        x = x0 + (1 if x0 > cx else -1) * filt * 260
        a = pp * clamp((u - 0.05) / 0.3) * (1 - filt * 0.92)
        particle(d, x, y0 + filt * 30, 9, cols[key], a, ring=True)
        if a > 0.4 and i % 6 == 0:
            tc(d, x, y0 + filt * 30, key, F("sans", 14), INK, a * 0.8, anchor="mm")
    ai = smooth((u - 0.5) / 0.35)
    if ai > 0:
        glow(img, cx, cy, 22, INK, ai)
        tc(d, cx, cy + 110, "味单态 · 没有味道", F("sansb", 28), YEL, ai, anchor="mm")
    # 左侧标签
    a3 = smooth((u - 0.1) / 0.25)
    tc(d, 150, 130, "u 上", F("sans", 20), BLUE, a3 * (1 - filt * 0.9), anchor="lm")
    tc(d, 150, 176, "d 下", F("sans", 20), RED, a3 * (1 - filt * 0.9), anchor="lm")
    tc(d, 150, 222, "s 奇异", F("sans", 20), YEL, a3 * (1 - filt * 0.9), anchor="lm")

def sc_hundred_billion(img, d, t, u):
    """24: 上百亿事例逐颗筛"""
    vgrad(img, (13, 15, 19), (8, 9, 13))
    pp = smooth((u - 0.02) / 0.25)
    cols, rows = 60, 20
    gx, gy = 40, 180
    cw, ch = (W - 80) / cols, 300 / rows
    k = clamp((u - 0.05) / 0.5)
    lit = int(cols * rows * ease_out(k))
    rnd = random.Random(88)
    for i in range(min(lit, cols * rows)):
        c_, r_ = i % cols, i // cols
        x = gx + c_ * cw + cw / 2
        y = gy + r_ * ch + ch / 2
        hot = rnd.random() < 0.06
        col = YEL if hot else (BLUE if rnd.random() < 0.5 else DIM)
        d.rectangle([x - cw * 0.32, y - ch * 0.3, x + cw * 0.32, y + ch * 0.3], fill=ca(col, pp * (0.85 if hot else 0.45)))
    tc(d, W / 2, 550, "100 亿 J/ψ 事例", F("serifb", 46), INK, pp * smooth((u - 0.25) / 0.3), anchor="mm")
    tc(d, W / 2, 596, "一颗一颗筛味道差异", F("sans", 24), DIM, pp * smooth((u - 0.45) / 0.3), anchor="mm")

def sc_2011_to_2026(img, d, t, u):
    """25: 十七年 + 四十年、五代人"""
    vgrad(img, (14, 16, 22), (8, 9, 13))
    pp = smooth((u - 0.02) / 0.25)
    tc(d, W / 2, 210, "17 年", F("serifb", 100), YEL, pp * smooth((u - 0.05) / 0.3), anchor="mm")
    # 一条从 2009 到 2026 的时间线
    x0, x1, y = 220, 1060, 360
    k = ease_io((u - 0.2) / 0.5)
    line(d, (x0, y), (lerp(x0, x1, k), y), BLUE, 2, pp * 0.7)
    for fr, lab in [(0, "2009"), (0.5, "2024 量子数"), (1.0, "2026 味单态")]:
        a = smooth((k - fr) / 0.08) * pp
        x = x0 + (x1 - x0) * fr
        d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=ca(INK, a))
        tc(d, x, y + 34, lab, F("sans", 20), DIM, a, anchor="mm")
    a2 = smooth((u - 0.55) / 0.3)
    tc(d, W / 2, 520, "往前追：40 年 · 五代人 · 近 700 人", F("sansb", 28), INK, a2, anchor="mm")

def sc_special(img, d, t, u):
    """26: 特别报告"""
    vgrad(img, (18, 15, 16), (8, 9, 13))
    pp = smooth((u - 0.05) / 0.3)
    # 会场座位俯视
    cx, cy = W / 2, 250
    for r in range(5):
        for c in range(16):
            x = cx + (c - 7.5) * 54
            y = cy + r * 34 + 20
            d.rounded_rectangle([x - 16, y - 10, x + 16, y + 10], radius=4, outline=ca(DIM, pp * 0.35), width=1)
    a2 = smooth((u - 0.3) / 0.3)
    tc(d, W / 2, 520, "第 43 届国际高能物理大会", F("sans", 26), INK, a2, anchor="mm")
    tc(d, W / 2, 576, "巴西 · 纳塔尔 · 2026 年 8 月 · 特别报告", F("sans", 22), YEL, a2, anchor="mm")

def sc_confirmed(img, d, t, u):
    """27: 确认了什么 —— 引号大字"""
    vgrad(img, (14, 16, 22), (8, 9, 13))
    pp = smooth((u - 0.03) / 0.3)
    tc(d, 240, 200, "\u201c", F("serifb", 120), BLUE, pp * 0.6, anchor="mm")
    lines = [("X(2370) 的主要成分", INK), ("是最轻的胶球", YEL)]
    for i, (s, col) in enumerate(lines):
        a = smooth((u - 0.1 - i * 0.15) / 0.3)
        tc(d, W / 2, 300 + i * 82, s, F("serifb", 52), col, a, anchor="mm")
    a3 = smooth((u - 0.55) / 0.3)
    tc(d, W / 2, 508, "五十年，最有底的一次", F("sans", 26), DIM, a3, anchor="mm")

def sc_2p5(img, d, t, u):
    """28: 2.37 GeV ≈ 2.5 个质子"""
    vgrad(img, (14, 16, 22), (8, 9, 13))
    pp = smooth((u - 0.02) / 0.25)
    cx, cy = W / 2, 330
    k = ease_out((u - 0.15) / 0.5)
    # 质子小方块 + 一个半
    for i in range(3):
        x = cx - 130 + i * 90
        s_ = 62
        frac = clamp((k - i * 0.22) / 0.4)
        col = RED if i == 2 else INK
        d.rectangle([x - s_ / 2, cy - s_ / 2, x + s_ / 2, cy - s_ / 2 + s_ * frac], fill=ca(col, pp * 0.8))
        d.rectangle([x - s_ / 2, cy - s_ / 2, x + s_ / 2, cy + s_ / 2], outline=ca(col, pp * 0.6), width=1)
    tc(d, cx + 40, cy + 100, "≈ 2.5 个质子", F("sans", 26), DIM, pp * smooth((u - 0.45) / 0.25), anchor="mm")
    tc(d, cx, 216, "2.37 GeV", F("serifb", 66), YEL, pp * smooth((u - 0.05) / 0.3), anchor="mm")

def sc_not_pure(img, d, t, u):
    """29: 不是纯胶球：混入普通夸克态"""
    vgrad(img, (16, 15, 18), (8, 9, 13))
    cx = W / 2
    pp = smooth((u - 0.02) / 0.25)
    R = 112
    cy = 340
    # 能量球
    rnd = random.Random(71)
    for i in range(70):
        ang = rnd.random() * 6.28 + t * 0.5
        rr = R * (0.2 + 0.8 * rnd.random())
        x, y = cx + math.cos(ang) * rr, cy + math.sin(ang) * rr * 0.92
        d.line([(x, y), (x + 10 * math.cos(ang + 1.5), y + 10 * math.sin(ang + 1.5))], fill=ca(YEL, pp * 0.45), width=2)
    d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=ca(INK, pp * 0.5), width=2)
    # 混进来的夸克
    for i in range(3):
        ang = math.radians(200 + i * 40) + t * 0.3
        x, y = cx + math.cos(ang) * 78, cy + math.sin(ang) * 66
        particle(d, x, y, 13, RED, pp * smooth((u - 0.3) / 0.3), ring=True)
    a2 = smooth((u - 0.45) / 0.3)
    tc(d, cx, cy + 210, "里面混着普通夸克态，比例未知", F("sansb", 28), RED, a2, anchor="mm")
    # 虚线比例问号
    if a2 > 0:
        tc(d, cx + 230, cy - 40, "?", F("serifb", 80), RED, a2 * 0.9, anchor="mm")

def sc_model(img, d, t, u):
    """30: 依赖模型 —— 三条不同的曲线"""
    vgrad(img, (14, 16, 22), (8, 9, 13))
    pp = smooth((u - 0.02) / 0.25)
    ox, oy = 300, 540
    a2 = pp * smooth((u - 0.1) / 0.3)
    line(d, (ox, oy), (ox + 760, oy), DIM, 2, a2 * 0.6)
    line(d, (ox, oy), (ox, oy - 340), DIM, 2, a2 * 0.6)
    k = clamp((u - 0.15) / 0.5)
    for j, (col, off) in enumerate([(BLUE, -40), (YEL, 0), (RED, 46)]):
        pts = []
        for i in range(100):
            x = ox + 40 + i * 7
            y = oy - 130 - off * 0.2 - 150 * math.exp(-((i - 60 - off * 0.3) / 30) ** 2)
            pts.append((x, y))
        m = int(len(pts) * ease_out(k))
        for i in range(max(m - 1, 0)):
            line(d, pts[i], pts[i + 1], col, 3, pp * 0.85)
    tc(d, W / 2, 150, "模型一换，数字会动", F("sansb", 30), INK, a2 * smooth((u - 0.5) / 0.3), anchor="mm")

def sc_moment(img, d, t, u):
    """31: 只存在一瞬"""
    vgrad(img, (13, 15, 20), (8, 9, 13))
    cx, cy = W / 2, 320
    pp = smooth((u - 0.02) / 0.2)
    # 周期闪烁
    ph = (t * 1.6) % 1.0
    a = pp * (0.15 + 0.85 * math.exp(-((ph - 0.12) ** 2) / 0.004))
    for i in range(3):
        pts = []
        N = 60
        for k in range(N + 1):
            ang = k / N * 2 * math.pi * (1.4 + 0.3 * i) + i
            rr = 38 * (0.6 + 0.4 * abs(math.sin(k / N * 3 * math.pi)))
            pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
        for k in range(len(pts) - 1):
            line(d, pts[k], pts[k + 1], YEL, 3, a)
    glow(img, cx, cy, 8, INK, a)
    a2 = smooth((u - 0.3) / 0.3)
    tc(d, W / 2, 470, "寿命：10⁻²³ 秒量级", F("serifb", 46), INK, a2, anchor="mm")
    tc(d, W / 2, 528, "拿不到手里，只能从碎片里认", F("sans", 24), DIM, a2 * smooth((u - 0.5) / 0.3), anchor="mm")

def sc_borders(img, d, t, u):
    """32: 三条边界 围成框"""
    vgrad(img, (16, 15, 18), (8, 9, 13))
    cx, cy = W / 2, 340
    pp = smooth((u - 0.02) / 0.25)
    # 中央小球
    for i in range(3):
        pts = []
        N = 70
        for k in range(N + 1):
            ang = k / N * 2 * math.pi * (1.2 + 0.4 * i) + t * 0.6 + i
            rr = 40 * (0.55 + 0.45 * abs(math.sin(k / N * 3 * math.pi + t * 0.5)))
            pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
        for k in range(len(pts) - 1):
            line(d, pts[k], pts[k + 1], YEL, 3, pp * 0.9)
    # 三条边界线依次画出
    L, T, R, B = cx - 380, cy - 210, cx + 380, cy + 210
    segs = [((L, B), (R, B)), ((R, B), (R, T)), ((R, T), (L, T)), ((L, T), (L, B))]
    labs = [("不是纯胶球", 0), ("依赖模型", 1), ("只存在一瞬", 2)]
    for i, ((p0, p1), (lab, _)) in enumerate(zip(segs, labs)):
        k = ease_out((u - 0.1 - i * 0.16) / 0.35)
        if k <= 0:
            continue
        p1c = (lerp(p0[0], p1[0], k), lerp(p0[1], p1[1], k))
        line(d, p0, p1c, BLUE, 2, pp * 0.7)
        tc(d, (p0[0] + p1[0]) / 2, p0[1] + (34 if i == 0 else (-34 if i == 2 else 0)),
           lab, F("sansb", 26), BLUE, pp * smooth((u - 0.25 - i * 0.16) / 0.25), anchor="mm")

def sc_border_value(img, d, t, u):
    """33: 边界＝价值"""
    vgrad(img, (16, 15, 18), (8, 9, 13))
    pp = smooth((u - 0.03) / 0.3)
    # 方框碎裂成光点
    cx, cy = W / 2, 330
    k = ease_io((u - 0.1) / 0.5)
    L, T, R, B = 300, 180, 980, 480
    xs = [L, R, R, L, L]; ys = [B, B, T, T, B]
    for i in range(4):
        a = (1 - k) * pp * 0.7
        line(d, (xs[i], ys[i]), (xs[i + 1], ys[i + 1]), BLUE, 2, a)
    a2 = smooth((u - 0.45) / 0.3)
    tc(d, cx, cy - 10, "规则，是真的", F("serifb", 62), YEL, a2, anchor="mm")
    tc(d, cx, cy + 86, "写在纸上的那套理论，第一次被实物验签", F("sans", 22), INK, a2 * 0.9, anchor="mm")

def sc_back_zero(img, d, t, u):
    """34: 回到 0 个夸克"""
    vgrad(img, (14, 16, 21), (8, 9, 13))
    cx, cy = W / 2, 320
    pp = smooth((u - 0.02) / 0.3)
    for i in range(3):
        pts = []
        N = 80
        for k in range(N + 1):
            ang = k / N * 2 * math.pi * (1.3 + 0.35 * i) + t * 0.7 + i * 1.1
            rr = 76 * (0.6 + 0.4 * abs(math.sin(k / N * 3 * math.pi + t * 0.6)))
            pts.append((cx + rr * math.cos(ang), cy + rr * 0.95 * math.sin(ang)))
        for k in range(len(pts) - 1):
            line(d, pts[k], pts[k + 1], mixc(YEL, BLUE, i / 2), 3, pp)
    glow(img, cx, cy, 16, INK, pp)
    tc(d, cx, cy + 160, "0 个夸克", F("serifb", 64), INK, pp * smooth((u - 0.2) / 0.3), anchor="mm")

def sc_particle_list(img, d, t, u):
    """35: 粒子名单，一格是高亮的"""
    vgrad(img, (14, 16, 21), (8, 9, 13))
    pp = smooth((u - 0.02) / 0.25)
    cols, rows = 18, 11
    gx, gy = 130, 130
    cw, ch = 58, 34
    hi_idx = 5 * cols + 11
    rnd = random.Random(99)
    for i in range(cols * rows):
        c_, r_ = i % cols, i // cols
        x = gx + c_ * cw
        y = gy + r_ * ch
        a = pp * (0.10 + 0.12 * rnd.random())
        if i == hi_idx:
            a = pp
        d.rounded_rectangle([x, y, x + cw - 12, y + ch - 12], radius=4,
                            outline=ca(YEL if i == hi_idx else DIM, a), width=2 if i == hi_idx else 1)
    hx = gx + (hi_idx % cols) * cw + cw / 2 - 6
    hy = gy + (hi_idx // cols) * ch + ch / 2 - 6
    if u > 0.3:
        glow(img, hx, hy, 7, YEL, pp)
        a2 = smooth((u - 0.35) / 0.3)
        tc(d, hx - 40, hy - 9, "X(2370)", F("serifb", 34), YEL, a2, anchor="rm")
    tc(d, W / 2, 600, "粒子名单 · 一格", F("sans", 22), DIM, pp * smooth((u - 0.2) / 0.3), anchor="mm")

def sc_not_weird(img, d, t, u):
    """36: 不是宇宙奇怪，是我们看错了主角"""
    vgrad(img, (16, 15, 18), (8, 9, 13))
    pp = smooth((u - 0.03) / 0.3)
    a1 = smooth((u - 0.08) / 0.28) * clamp((0.62 - u) / 0.16)
    a2 = smooth((u - 0.34) / 0.3)
    tc(d, W / 2, 300, "夸克是主角", F("serifb", 66), DIM, a1, anchor="mm")
    tc(d, W / 2, 300, "力才是主角", F("serifb", 72), YEL, a2, anchor="mm")
    tc(d, W / 2, 400, "夸克只是骨头缝，胶子才是肉", F("sans", 28), INK, a2, anchor="mm")

def sc_knot_final(img, d, t, u):
    """37: 力打的结 —— 无数结在空间里"""
    vgrad(img, (15, 14, 18), (8, 9, 13))
    dots(img, t, n=110, bright=0.35)
    cx, cy = W / 2, 320
    pp = smooth((u - 0.03) / 0.3)
    k = ease_out((u - 0.1) / 0.5)
    for i in range(3):
        pts = []
        N = 90
        for j in range(N + 1):
            ang = j / N * 2 * math.pi * (1.3 + 0.4 * i) + t * 0.5 + i * 1.05
            rr = 70 * (0.6 + 0.4 * abs(math.sin(j / N * 3 * math.pi + t * 0.4)))
            pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
        for j in range(len(pts) - 1):
            line(d, pts[j], pts[j + 1], mixc(YEL, BLUE, i / 2), 3, pp)
    # 远处更多小结点
    rnd = random.Random(17)
    for i in range(int(40 * k)):
        ang = rnd.random() * 6.28
        dist = 220 + rnd.random() * 380
        x = cx + math.cos(ang) * dist * 1.3
        y = cy + math.sin(ang) * dist * 0.7
        a = pp * 0.35 * k
        d.ellipse([x - 9, y - 9, x + 9, y + 9], outline=ca(YEL, a), width=1)
        d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=ca(INK, a))
    tc(d, cx, cy + 150, "物质，是力打的结", F("serifb", 44), INK, pp, anchor="mm")

def sc_outro(img, d, t, u):
    """38: 收尾提问 + 片尾"""
    vgrad(img, (13, 15, 20), (6, 7, 10))
    dots(img, t, n=120, bright=0.4)
    cx, cy = W / 2, 300
    pp = smooth((u - 0.02) / 0.3)
    rnd = random.Random(19)
    for i in range(60):
        ang = rnd.random() * 6.28
        dist = 60 + rnd.random() * 380
        x = cx + math.cos(ang) * dist * 1.25
        y = cy + math.sin(ang) * dist * 0.7
        a = pp * (0.12 + 0.3 * rnd.random()) * (0.6 + 0.4 * math.sin(t * 1.5 + i))
        d.ellipse([x - 4, y - 4, x + 4, y + 4], outline=ca(YEL, a), width=1)
    a1 = smooth((u - 0.05) / 0.3)
    a2 = smooth((u - 0.3) / 0.3)
    tc(d, cx, 300, "还有多少个结", F("serifb", 66), INK, a1, anchor="mm")
    tc(d, cx, 380, "是我们还没找到的？", F("serifb", 66), YEL, a2, anchor="mm")
    a3 = smooth((u - 0.62) / 0.3)
    tc(d, cx, 520, "科普爆点动画周刊 · 第 04 期 · 下期见", F("sans", 22), DIM, a3, anchor="mm")

def sc_end(img, d, t, u):
    vgrad(img, (8, 9, 12), (6, 7, 10))
    pp = smooth(u / 0.4) * clamp((1 - (u - 0.86) / 0.14) if u > 0.86 else 1.0)
    tc(d, W / 2, 330, "零个夸克", F("serifb", 72), INK, pp, anchor="mm")
    tc(d, W / 2, 410, "科普爆点动画周刊 · 第 04 期", F("sans", 22), DIM, pp, anchor="mm")


# ---------------- 追加场景（按字幕段驱动） ----------------
def sc_gluon_self(img, d, t, u):
    """胶子自相互作用：三线汇聚成结"""
    vgrad(img, (14, 17, 22), (8, 9, 13))
    cx, cy = W / 2, 360
    pp = smooth((u - 0.02) / 0.25)
    k = ease_io((u - 0.05) / 0.5)
    cols = [YEL, BLUE, RED]
    for i in range(3):
        ang0 = -math.pi / 2 + i * 2 * math.pi / 3
        R = lerp(250, 60, k)
        x = cx + math.cos(ang0) * R
        y = cy + math.sin(ang0) * R * 0.9
        spring(d, (x, y), (cx, cy), cols[i], pp * (0.4 + 0.6 * k), n=6, amp=12 * (1 - k * 0.5), w=3, phase=t * 5 + i)
        particle(d, x, y, 13, cols[i], pp)
    e = smooth((u - 0.35) / 0.35)
    glow(img, cx, cy, 16 + 12 * e, mixc(YEL, INK, 0.5), pp * (0.5 + 0.5 * e))
    tc(d, W / 2, 560, "胶子 → 胶球", F("serifb", 36), INK, pp * e, anchor="mm")

def sc_mass_conservation(img, d, t, u):
    """能量守恒：胶子无质量，能量锁在球里"""
    vgrad(img, (15, 16, 21), (8, 9, 13))
    cx, cy = 440, 360
    pp = smooth((u - 0.02) / 0.25)
    R = 112
    d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=ca(INK, pp * 0.55), width=2)
    rnd = random.Random(9)
    for i in range(60):
        ang = rnd.random() * 6.28
        rr = R * (0.25 + 0.72 * rnd.random())
        x, y = cx + math.cos(ang) * rr, cy + math.sin(ang) * rr
        sp = 0.6 + rnd.random()
        vx, vy = -math.sin(ang + t * sp) * 26, math.cos(ang + t * sp * 1.2) * 26
        d.line([(x, y), (x + vx * 0.5, y + vy * 0.5)], fill=ca(YEL, pp * 0.6), width=2)
    for i in range(4):
        ang = t * 1.4 + i * 1.57
        glow(img, cx + math.cos(ang) * 70, cy + math.sin(ang) * 70, 7, YEL, pp, 1.0)
    # 左：0 质量；右：能量读数
    a2 = smooth((u - 0.2) / 0.3)
    tc(d, 870, 300, "胶子静止质量", F("sans", 22), DIM, a2, anchor="mm")
    tc(d, 870, 356, "0", F("serifb", 72), BLUE, a2, anchor="mm")
    a3 = smooth((u - 0.55) / 0.25)
    tc(d, 870, 432, "能量：锁在球里", F("sans", 22), YEL, a3, anchor="mm")
    tc(d, W / 2, 560, "跑不掉的能量，就是质量", F("serifb", 34), INK, a3 and smooth((u - 0.68) / 0.25) or 0, anchor="mm")

def sc_bar99(img, d, t, u):
    """99% 铺满屏幕"""
    vgrad(img, (26, 22, 13), (10, 10, 12))
    cx, cy = W / 2, 330
    pp = smooth((u - 0.02) / 0.3)
    k = ease_out((u - 0.05) / 0.45)
    # 底部油箱填充
    h = lerp(0, 560, k)
    d.rectangle([0, H - h, W, H], fill=ca(YEL, pp * 0.85))
    for i in range(40):
        yy = H - (i / 40) * h
        d.line([(0, yy), (W, yy)], fill=ca(mixc(YEL, (255, 255, 255), 0.25), pp * 0.12), width=1)
    tc(d, cx, 300, "99%", F("serifb", 140), BG if k > 0.55 else INK, pp, anchor="mm")
    tc(d, cx, 410, "你身体的重量，几乎全是力变的", F("sansb", 30), BG if k > 0.55 else INK, pp * smooth((u - 0.4) / 0.3), anchor="mm")

def sc_flavor_intro(img, d, t, u):
    """味单态：三种味道三扇门"""
    vgrad(img, (15, 16, 21), (8, 9, 13))
    pp = smooth((u - 0.02) / 0.25)
    cols = [BLUE, RED, YEL]
    names = ["上 u", "下 d", "奇异 s"]
    for i in range(3):
        x = W / 2 + (i - 1) * 260
        k = ease_out((u - 0.05 - i * 0.08) / 0.35)
        d.rounded_rectangle([x - 80, 320 - 100 * k, x + 80, 320 + 100 * k], radius=10, outline=ca(cols[i], pp * 0.9), width=3)
        particle(d, x, 320, 16, cols[i], pp * smooth((u - 0.2 - i * 0.08) / 0.25))
        tc(d, x, 470, names[i], F("sans", 24), cols[i], pp * smooth((u - 0.15 - i * 0.08) / 0.25), anchor="mm")
    a2 = smooth((u - 0.5) / 0.3)
    tc(d, W / 2, 560, "普通粒子：只属于一扇门", F("sansb", 28), INK, a2, anchor="mm")

def sc_knot_small(img, d, t, u):
    """收尾：小球在画面中间，留白给解说"""
    vgrad(img, (13, 15, 20), (7, 8, 11))
    dots(img, t, n=110, bright=0.4)
    cx, cy = W / 2, 350
    pp = smooth((u - 0.02) / 0.3)
    for i in range(3):
        pts = []
        N = 80
        for j in range(N + 1):
            ang = j / N * 2 * math.pi * (1.3 + 0.35 * i) + t * 0.6 + i * 1.1
            rr = 42 * (0.6 + 0.4 * abs(math.sin(j / N * 3 * math.pi + t * 0.6)))
            pts.append((cx + rr * math.cos(ang), cy + rr * 0.95 * math.sin(ang)))
        for j in range(len(pts) - 1):
            line(d, pts[j], pts[j + 1], mixc(YEL, BLUE, i / 2), 3, pp)
    glow(img, cx, cy, 10, INK, pp)

_SCENE_FN = {
    "sc_open1": sc_open1, "sc_open2": sc_open2, "sc_you": sc_you, "sc_proton": sc_proton,
    "sc_snap": sc_snap, "sc_more": sc_more, "sc_gluon_sep": sc_gluon_sep,
    "sc_three_colors": sc_three_colors, "sc_gluon_self": sc_gluon_self, "sc_knot": sc_knot,
    "sc_glueball_label": sc_glueball_label, "sc_forty_years": sc_forty_years,
    "sc_mass_conservation": sc_mass_conservation, "sc_energy_mass": sc_energy_mass,
    "sc_emc2": sc_emc2, "sc_heavier": sc_heavier, "sc_quark_1pct": sc_quark_1pct,
    "sc_mass_originates": sc_mass_originates, "sc_bar99": sc_bar99,
    "sc_glue_not_water": sc_glue_not_water, "sc_collider": sc_collider, "sc_2009": sc_2009,
    "sc_noise": sc_noise, "sc_three_checks": sc_three_checks, "sc_flavor_intro": sc_flavor_intro,
    "sc_check1_mass": sc_check1_mass, "sc_check2_spin": sc_check2_spin,
    "sc_hundred_billion": sc_hundred_billion, "sc_2011_to_2026": sc_2011_to_2026,
    "sc_special": sc_special, "sc_confirmed": sc_confirmed, "sc_2p5": sc_2p5,
    "sc_not_pure": sc_not_pure, "sc_model": sc_model, "sc_moment": sc_moment,
    "sc_borders": sc_borders, "sc_border_value": sc_border_value, "sc_back_zero": sc_back_zero,
    "sc_particle_list": sc_particle_list, "sc_not_weird": sc_not_weird,
    "sc_knot_final": sc_knot_final, "sc_knot_small": sc_knot_small, "sc_end": sc_end,
}

# 分镜表由 src/scenes.json 驱动（gen_segs.py 生成），不再手写下标。
# 因此增删解说句、调整句子长短，都不会再让画面和解说错位。
_PLAN = json.load(open(os.path.join(HERE, "scenes.json"), encoding="utf-8"))
SCENES = []
for _k, _b in enumerate(_PLAN):
    _t0 = TL[_b["r0"]]["start"] if _b["r0"] > 0 else 0.0
    _t1 = TL[_PLAN[_k + 1]["r0"]]["start"] if _k + 1 < len(_PLAN) else TOTAL + 1
    SCENES.append((_t0, _t1, _SCENE_FN[_b["key"]]))
# 从「四十年前」这一场开始加顶部/底部遮罩，给大字和字幕让位
MASK_T = next((s[0] for s in SCENES if s[2] is sc_forty_years), 0.0)

def fade(img, a):
    if a >= 0.999:
        return img
    base = Image.new("RGB", (W, H), BG)
    return Image.blend(base, img, clamp(a))

def render_at(t):
    scen = SCENES[-1]
    for s in SCENES:
        if s[0] <= t < s[1]:
            scen = s
            break
    t0, t1, fn = scen
    u = clamp((t - t0) / max(t1 - t0, 0.01))
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img, "RGBA")
    if t0 >= MASK_T:
        hl(img, 0, 170, W, 60)
        hl(img, 0, 600, W, 120)
    fn(img, d, t, u)
    # 场景切换简易交叉：首个 0.35s 从暗入，末尾 0.3s 出（只对非首尾）
    a_in = smooth(min(1.0, (t - t0) / 0.35)) if t0 > 0.01 else 1.0
    a_out = 1.0
    if t1 < 999:
        a_out = 1.0 - 0.35 * smooth((t - (t1 - 0.3)) / 0.3)
    img = fade(img, min(a_in, a_out))
    d = ImageDraw.Draw(img, "RGBA")
    caption(img, d, t)
    hud(img, d, t)
    subtitle(img, d, t)
    return img
