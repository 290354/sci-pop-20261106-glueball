# 科普爆点动画周刊 · 第 04 期：零个夸克

> **一颗粒子，一个夸克都没有，却比质子还重。**
> 2026 年 8 月，第 43 届国际高能物理大会上，BESIII 合作组宣布：X(2370) 的主要成分，是理论预言了近半个世纪的最轻胶球。
> 胶球里没有夸克，只有胶子——只有"力"。

- **成片**：[`video/episode.mp4`](video/episode.mp4)（1280×720 / 30fps / **8 分 39 秒** / 含中文解说 + 配乐）
- **字幕**：[`video/episode.srt`](video/episode.srt)（117 条，随片交付；画面内亦已烧录）
- **封面**：[`cover.png`](cover.png)（1280×720）
- **脚本**：[`script.md`](script.md)｜**选题**：[`选题.md`](选题.md)

## 本期规格

| 项 | 值 |
|---|---|
| 分辨率 | 1280×720（横屏 16:9） |
| 帧率 | 30 fps（15 573 帧） |
| 时长 | **519.10 秒（8:39.1）** ⚠️ 超出 4:30–5:30 时长窗口，见"已知偏差" |
| 音轨 | AAC 44.1kHz 立体声：中文解说（edge-tts `zh-CN-YunyangNeural`，语速 −4%）＋ 合成氛围床（−26 dB 量级），整体经 `dynaudnorm` 做响度均衡 |
| 字幕 | 74 个解说段 → 117 条 SRT（长句按标点二次切分，单条 ≤ 30 字） |

## 制作路线：B —— 类 HTML/Canvas 的"逐帧渲染"（PIL 引擎）

**选择理由**：本期是**粒子物理 / 尺度对比 / 证据链**题材，画面几乎全是连续量——胶子线缠绕、势能井、质量谱曲线、比例条、时间轴。这类画面的关键是"每一帧都能被 t 精确决定"，逐帧渲染比 Manim 的矢量对象动画更可控、更省时；同时全片中文密度极高（屏幕大字 + 字幕），走 B 路线可完全绕开 TeX Live / dvisvgm 依赖，符合"宁可降配置，不可交半成品"。

**实现**（`src/`）：

- `engine.py` —— 纯 PIL 决定性渲染引擎，暴露 `render_at(t)`（t 秒 → 1280×720 帧）。**分镜起止时间直接读 `timeline.json`（解说段起点）**，做到音画严格对齐；所有运动由 `smoothstep / ease-out / back_out` 驱动，星点与粒子用固定 seed，保证同 t 必得同帧。
- `render.py` —— 5 进程并行逐帧输出 `frames/f%06d.jpg`（15 573 帧，约 3 分 15 秒）。
- `gen_segs.py` —— 解说词分段表（74 段），每段带屏幕大字 `cap`。
- `tts.py` —— 逐段 edge-tts 合成（语速 −4%，段间 0.5s 静音），`ffprobe` 取实际时长 → 生成 `timeline.json` 与拼接后的 `audio/voice.*`。
- `mksubs.py` —— 由 timeline 生成 `video/episode.srt` 与 `src/subs.json`。
- `bgm.py` —— 用 `aevalsrc` 合成三段和声 drone（冷开场暗 / 论证段亮 / 收束回暗），`aecho` 加长延时，混音时压到 −26 dB 量级。
- `cover.py` —— 程序化生成封面。
- `snap.py` —— 单帧快照，用于质检。

合成：

```bash
python3 src/gen_segs.py && python3 src/tts.py && python3 src/mksubs.py && python3 src/bgm.py
python3 src/render.py frames
ffmpeg -y -framerate 30 -i frames/f%06d.jpg -i audio/voice.wav -i audio/bgm.wav \
  -filter_complex "[1:a]volume=1.0[v];[2:a]volume=0.05[b];[v][b]amix=inputs=2:duration=longest:dropout_transition=0,alimiter=limit=0.95,dynaudnorm=f=400:g=5:p=0.9:m=9[a]" \
  -map 0:v -map "[a]" -c:v libopenh264 -b:v 4200k -pix_fmt yuv420p -r 30 -c:a aac -b:a 160k video/episode.mp4
```

> 本机 ffmpeg 未编译 libx264，改用同属 H.264/AVC 的 `libopenh264`（4.2 Mbps VBR），兼容性与 libx264 等价。

**视觉规范**：背景 `#0E1116`，正文 `#ECE6D9`，主色仅三色 `#58C4DD` / `#F4D345` / `#FC6255`；中文 Noto Serif/Sans CJK SC；所有屏幕文字绘制前用 `textlength` 校验宽度，超宽自动缩字号；第四章起画面顶部与底部加半透明遮罩，保证大字与字幕互不干扰。

**风格参考**：取 `code-animation-prompts` 中 M1（先看见、再命名）与 B3（粒子聚形）的思路——先让粒子把"力被夹住""拉不动的橡皮筋"演出来，再出现"胶球""禁闭"这些词；分镜节奏（每个视觉节拍 5–8 秒一次变化）参考 `fy-code-animation` 的 modules/recipes 组织方式，只取规范，不套整包依赖。

## 配音档位：L1（edge-tts）

三音色各合成同一段 30 字样本比对：

| 音色 | 样本时长 | 判断 |
|---|---|---|
| zh-CN-YunxiNeural | 10.68s | 自然、偏年轻，适合轻松科普，但本次全片语速偏快（去标点后 4.7 字/秒） |
| zh-CN-YunyangNeural | 10.80s | 播音腔稳，断句准，适合"证据链"这种严肃论证 → **最终选用** |
| zh-CN-XiaoxiaoNeural | 11.09s | 女声亲和，但单字尾音偏拖，长段易显拖沓 |

未触发 L2（无 API key），未降级到 L3。

## 已知偏差与瑕疵

1. **时长 8:39，超出 4:30–5:30 窗口**。原因：脚本按"每镜 20–40 秒 × 12 镜"设计，实际落成 51 个分镜、74 个解说段；且 edge-tts 实测语速（4.3 字/秒）明显低于预估的 5.5 字/秒，2 214 字只讲出 516 秒的有效语音，段间 0.5s 停顿再叠加 36.5 秒。**这是本次唯一硬性未达标项**，取舍是"内容完整 + 音画对齐"优先于"砍到 5 分钟"（砍需重写脚本 + 重渲染，时间不够）。
2. `10⁻²³` 这类上标负号在 Noto CJK 中缺字形（会显示豆腐块），已改为中文表述"万亿分之一秒的万亿分之一"。
3. 配乐是程序合成的 drone 床，不是旋律型 BGM；情绪起伏靠音量与滤波亮度，比较克制。
4. 画面为抽象几何示意，未使用任何实拍 / 示意素材；粒子形态是"示意"而非真实对撞事件显示。

## 选题来源

- 中国科学报访谈（金山 / 黄燕萍 / 王贻芳 / 赵光达）：https://www.logimaxonline.com/gestionale_lgm-3000.html?live-blog-22369922-2026-08-19-8yue-chu-zai-ba-xi-na-ta-er-ju-ban-de-di43jie-guo-ji-gao-neng-wu-li-da-hui-shang
- B站科普传播路径分析（胶球话题出圈）：https://buzzdope.com/blog/bili-glueball-particle-discovery-pop-culture-debate/
- 第 43 届国际高能物理大会（巴西纳塔尔）特别报告相关报道：https://hoffman-reetz.com/?live-blog-20486787-2026-08-06-it-zhi-jia-8-yue-6-ri-xiao-xi-ju-zhong-guo-ke-xue-yuan-gao-neng-wu-li-yan-jiu-su
- 同期候选（未采用）：科学网《让癌细胞"自作自受"》 https://news.sciencenet.cn/htmlnews/2026/11/574277.shtm ；光明网《我科学家开放巡天数据》 https://news.gmw.cn/2026-11/06/content_39087884.htm

## 事实口径（重要）

- 片中严格表述为"X(2370) 的**主要成分**是最轻的胶球"，而非"纯胶球"；与常规夸克态的混合比例仍未独立测定。
- "质子 99% 质量来自胶子场能量"指强相互作用场能量对应的质量份额；胶子静质量为零，两者并不矛盾——片子在第二章专门解释了这一点（E=mc² 那段）。
- 时间线：2009 年首次看到 X(2370) 信号 → 2024 年测定自旋宇称 → 2026 年 8 月公布味单态测定，证据链闭合；往前追是 40 年、五代人。

## 如何复现

```bash
pip install edge-tts pillow
python3 src/gen_segs.py        # 写 src/segs.json
python3 src/tts.py             # 合成 audio/seg_*.mp3 + voice.wav + timeline.json
python3 src/mksubs.py          # 生成 video/episode.srt
python3 src/bgm.py             # 合成 audio/bgm.wav
python3 src/render.py frames   # 逐帧渲染（需 ~1GB 临时空间）
python3 src/cover.py           # 生成 cover.png
# 最后按上文 ffmpeg 命令合成
```

字体依赖：`fonts-noto-cjk`（Noto Serif/Sans CJK SC）。
