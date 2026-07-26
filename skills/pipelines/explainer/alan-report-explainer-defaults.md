# Alan 研报解说产线默认（OM-localv1 落地）

> 与 skill `design-report-explainer` 同步。本文件给 **OpenMontage-localization-v1** 内 research/script/asset/publish/compose director 与 run 内脚本对齐用。
> 权威细节仍以 `agent-workspace/skills-staging/design-report-explainer/references/*` 为准。
> 达标范例 run：`projects/gs-agentic-ai-moats-xhs-20260724/`

## 账号与简介（封面顶栏 / 发布简介 / 口播 callback）

| 平台 | 名 | 简介 |
|------|----|------|
| 小红书 | **Astra 的 AI 趋势笔记** | 🤖 聚焦全球 AI 产业与科技趋势 · 📊 拆解算力｜芯片｜光模块｜上游供应链 · 💡 每天一条干货，用数据看懂 AI 浪潮 |
| 抖音 | **Astra 聊 AI** | 每天拆解 AI 产业的真实数据 · 芯片｜算力｜光模块｜上游供应链 · 只讲干货不吹水，跟着 Astra 看懂 AI 趋势 |
| YouTube | **Astra AI Insights** | Breaking down global AI trends, supply chains, and tech industry data with Astra. From semiconductors and AI infrastructure to cutting-edge tech developments — we turn complex research into clear, actionable insights. |

**口播 callback（必写）**

- XHS 开场固定：「整理了好久的数据，希望对大家有用～」→ 结尾收藏 CTA + 笔记气质
- DY 片尾：「关注 Astra 聊 AI，每天一条产业干货」
- YT 片尾英文对齐简介第一句 value prop
- 画面禁止投行 Logo；来源放旁白/片尾

## 锁死音频

```
XHS: voice_id=female-chengshu-jingpin  speed=1.2  narr_vol=1.0  bgm_vol=0.32  atempo=1.0
DY:  voice_id=male-qn-jingying-jingpin speed=1.2  narr_vol=1.0  bgm_vol=0.32  atempo=1.0
BGM: 低爆点/低峰谷；烫源先 loudnorm；两端可同曲
DY deliverable: 35–45MB @ ~3.5min → CBR video ~1400k (+ AAC 192k); must set -minrate=-maxrate
Disk: renders/final_{xhs,dy}.mp4 + exports/.../final.mp4 hardlink only — never also copy final_dy.mp4
```

写入 `artifacts/edit_decisions.json`、`scene_spec.bgm_volume`、`composition.json` music.volume、run 内 `gen_tts.py`。

## NotebookLM（research 开局）

若存在 `assets/notebooklm/` 或用户路径：

1. 一页概述 → `research_brief.pillars[]`
2. Quiz → `research_brief.quiz_bank[]` → publish `pinned_comments.txt`
3. Infographic 乱码 → 重绘，不进成片原图
4. 禁止 Buy/Sell/目标价进视频
5. 参考音频先 ASR：提关键数字、类比、转折与每 30 秒新主张/证据/机制；脚本若更稀，先补信息再过闸
6. 复杂 PPT 字体/溢出先修源 PPTX并导出 PDF；用户要求时放 `reader_bonus/`，不得附原研报

## 人审闸门（批准不跨级）

proposal → 双平台 script → 双平台 scene_plan → **试听与静帧** → 成片/发布包。

- “批双平台脚本”只授权进入分镜
- “批双平台分镜”只授权生成试听与静帧
- 试听与静帧：两平台代表性 TTS + 双封面 + 所选 runtime 开场 + 最复杂竖屏图表
- A/B 选择与 runtime 属于当期决定，不写成全局默认
- 未批试听与静帧，不做全量付费资产

## 钩子与信息密度

- 钩子优先用“近期市场/舆论表象 vs 研报需求或产能数据”的可证伪矛盾，前 30 秒亮出双方，正文用机制链、数字、风险闭环。
- 每 20–30 秒至少推进一个新主张、证据或机制；不靠加速 TTS 伪造密度。

## Astra 右上 + 底栏进度（compose 必读 · 复用勿自建）

> 完整规格：skill `design-report-explainer/references/astra-chrome.md`  
> **实现源码（复制）：** `projects/gs-agentic-ai-moats-xhs-20260724/render_fallback.py`  
> （`astra_progress` / `astra_showcase` / `_load_bgm_energy` 整段）

### 资产（不要另找视觉）

| 角色 | 路径 |
|------|------|
| 唯一权威 sheet | `~/agent-workspace/artifacts/hatch-pet/astra-20260716/final/spritesheet-extended.png` |
| run 内拷贝 | `assets/brand/spritesheet-extended.png` |
| 单元格 | 192×208，RGBA 切格；**禁止** chroma-key / 改色 / 用 decoded 碎帧 |

开局：`cp` 权威 sheet → `assets/brand/`；渲染脚本从范例 run `cp` 或移植 Astra 函数。**禁止** agent 自建宠物、seedream 生吉祥物、另装 Remotion 宠物包。

### 底栏进度条

- 全片一条 track（非逐场景呼吸条）
- tip = sheet **row 1 running-right** 循环；**每帧一只**狐贴在填充端
- `global_frac` = 全局帧 / 全片总帧

### 右上 showcase

- 尺寸≈字幕卡高（~180）；**右边距≥128**（防小红书裁尾）；无白卡片；边缘 feather 去晕
- **一整行姿态播完**再换行；换哪一行 = 本片 BGM RMS（calm→idle/wait/wave，hot→jump/run/fail）
- hold：calm 36 / mid 24 / hot 14 帧@30fps
- **禁用** sheet row 1（留给底栏）；禁用写死秒表换姿态

### QA

抽帧确认：右上有狐、底栏一只 tip、狐色=sheet 原色、无白托盘。

## 封面（publish）

Run 内脚本模式（范例 `make_covers.py`）：

1. XHS 1080×1440 笔记分层封
2. DY 1080×1920 大字封
3. `ffmpeg` 抽 `cover_from_video.png`

输出：`exports/<slug>/{xhs,dy}/covers/`

**成片开场：** 把设计封面垫成 1080×1920，片头 **≈2s** 静帧；混音时旁白 `adelay=2000`，该秒仅 BGM。`render_fallback.py` 已实现 cover_hold。尾帧再垫 ~0.45s，避免口播 disclaimer 被裁。

外部生图只做无字底图；Gemini prompt 契约见 skill `references/covers.md`。头像只在品牌初始化时生成一次，批准后锁定，不随每期重抽；prompt 见 `references/production-defaults.md`。

## 发布正文（publish）

强制 skill `design-report-explainer/references/caption-body.md`：

1. 几句说清视频是什么（3 秒判断）
2. 正文自然语言命中 2–3 领域关键词（搜索；不只靠 #）
3. 结尾互动问：小红书 **开放思考型** / 抖音 **开放争议·辩论型**

## 竖屏图表

scene_plan / render：KPI、对照、时间轴 **上下堆叠**；字幕偏上（XHS）；禁生产备注进 UI。

## Director 钩子

| Director | 增量 |
|----------|------|
| research | NotebookLM pillars + quiz_bank + ASR density；复杂 PPT 修复清单 |
| script | 反常识矛盾钩子；账号 callback；XHS 开场固定句；密度复核；测验 CTA |
| scene_plan | 双平台分镜闸门；最复杂图表列为静帧样片 |
| asset | 先试听与静帧闸门；锁死 voice/speed/bgm_vol；**拷贝 Astra sheet 到 assets/brand** |
| compose | **复用范例 render_fallback Astra chrome**；竖堆叠；全片进度条；cover_hold；**DY 成片 CBR≈1400kbps → 35–45MB**（防抖音低质标；须 minrate）；**exports/final.mp4 hardlink，禁双份** |
| publish | 双封面 + cover_from_video；quiz 钉评；**正文三原则**；按需 `reader_bonus` |
