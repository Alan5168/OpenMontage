# Alan 研报解说产线默认（OM-localv1 落地）

> 与 skill `design-report-explainer` 同步。本文件给 **OpenMontage-localization-v1** 内 research/script/asset/publish/compose director 与 run 内脚本对齐用。
> 权威细节仍以 `agent-workspace/skills-staging/design-report-explainer/references/*` 为准。
> 历史生产 run 可删除，不承担模板职责；规范只住本文件、`design-report-explainer` references 与 director。
>
> **发布端（2026-08-08）**：小红书 + B站竖屏。`dy/` = B站竖屏交付键（历史抖音目录名保留）。

## 账号与简介（封面顶栏 / 发布简介 / 口播 callback）

| 平台 | 名 | 简介 |
|------|----|------|
| 小红书 | **Astra 的 AI 趋势笔记** | 🤖 聚焦全球 AI 产业与科技趋势 · 📊 拆解算力｜芯片｜光模块｜上游供应链 · 💡 每天一条干货，用数据看懂 AI 浪潮 |
| B站竖屏（dir=`dy`） | **Astra 聊 AI** | 每天拆解 AI 产业的真实数据 · 芯片｜算力｜光模块｜上游供应链 · 只讲干货不吹水，跟着 Astra 看懂 AI 趋势 |
| YouTube | **Astra AI Insights** | Breaking down global AI trends, supply chains, and tech industry data with Astra. From semiconductors and AI infrastructure to cutting-edge tech developments — we turn complex research into clear, actionable insights. |

**口播 callback（必写）**

- XHS 开场：**观众生活/行情焦虑先行** → 研报定心丸/打脸 → 机制数字（**禁**「投研翻到研报很有用」作第一句；**禁**硬绑「整理了好久的数据」）→ 结尾开放思考 / A·B + 笔记气质
- B站竖屏开场：第一句**更绝对/争议/通俗**的生活或争论钩子，再进研报证据；片尾「关注 Astra 聊 AI，每天一条产业干货」
- YT 片尾英文对齐简介第一句 value prop
- 画面禁止投行 Logo；来源放旁白/片尾
- 开场画面：前 3 秒静图/信息图 + 醒目字幕（详见 skill「开场设计」）；开场自检：普通人是否觉得「跟我有关」

## 锁死音频

```
XHS: voice_id=female-chengshu-jingpin  speed=1.2  narr_vol=1.0  bgm_vol=0.32  atempo=1.0
BILI/dy: voice_id=male-qn-jingying-jingpin speed=1.2  narr_vol=1.0  bgm_vol=0.32  atempo=1.0
BGM: 低爆点/低峰谷；烫源先 loudnorm；两端可同曲
BILI/dy deliverable: 35–45MB @ ~3.5min → CBR video ~1400k (+ AAC 192k); must set -minrate=-maxrate
Disk: scratch=renders/work/{xhs,dy} (overwrite on rerender); renders/final_{xhs,dy}.mp4 + exports/.../final.mp4 hardlink only
GC: package-ready remove scratch/frames/clips/overlays/temp audio/backups; target <=250MB/run; published run -> Trash
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

## 人审策略（2026-07-26：成片前免中途审批）

与 skill `design-report-explainer` 对齐：**按需跑从给料到发布包就绪，中间不向 CEO 要审批**。

- proposal / script / scene_plan / 试听静帧 / 成片：agent 按本 defaults + skill **自决并落盘** `decision_log`
- CEO 给料即视为本 run 对已配置 provider/model 的 full-run preauthorization；常规生成、重出与 TTS 不逐次报模型/张数/费用，cost 字段只作内部 schema bookkeeping
- **唯一 CEO 闸**：真正上传小红书/B站（2026-08-08 起第二端为 B站竖屏，不再默认抖音）
- 定时无人值守仍须先过 STOP #17 的自动化授权；获批后不另设费用闸
- 内部可自检 TTS/封面/开场/复杂图，不合格重做，不要停问

## R0 语义配方准入（全量 assets 前）

- 从完整 brief 机械选 hook、最抽象主张、最密帧至少三张，覆盖 XHS/DY；
- 先生成无字底图 + 原生画幅叠字 proof，遮字后须读出声明关系；
- `design-flash-infographic/scripts/validate_semantic_r0.py` 必须输出 `SEMANTIC_R0_PASS`，才允许批量资产/TTS/compose；
- R0 失败自动重出底图或换 topology/recipe，最多 3 次；仍失败记 `R0_SEMANTIC_BLOCKED`，不做 final，不向 CEO 提出费用/豁免选择；
- R0 使用 `semantic-r0-v2`：除整页遮字 proof 外，每个文字模块必须以 required/observed `module_anchor_map` 绑定不同的可指认底图对象；整体相关但逐模块错配不得批量。独立审查晚期发现 `asset_semantics/topology/recipe` 时状态为 `VALID_R0_ESCAPE`，回流 R0 且不消耗 L1 轮次。

## 钩子与信息密度

- 钩子优先用“近期市场/舆论表象 vs 研报需求或产能数据”的可证伪矛盾，前 30 秒亮出双方，正文用机制链、数字、风险闭环。
- 每 20–30 秒至少推进一个新主张、证据或机制；不靠加速 TTS 伪造密度。

## Astra 右上 + 底栏进度（compose 必读 · 复用勿自建）

> 完整规格：skill `design-report-explainer/references/astra-chrome.md`  
> **实现规范：** skill `design-report-explainer/references/astra-chrome.md`。在已选 runtime 内实现，禁止复制历史 run 的整套 `render_fallback.py`。

### 资产（不要另找视觉）

| 角色 | 路径 |
|------|------|
| 唯一权威 sheet | `~/agent-workspace/artifacts/hatch-pet/astra-20260716/final/spritesheet-extended.png` |
| run 内拷贝 | `assets/brand/spritesheet-extended.png` |
| 单元格 | 192×208，RGBA 切格；**禁止** chroma-key / 改色 / 用 decoded 碎帧 |

开局：`cp` 权威 sheet → `assets/brand/`；渲染按 `astra-chrome.md` 在已选 runtime 内实现。**禁止** agent 自建宠物、seedream 生吉祥物、复制历史 run 整套脚本或另装 Remotion 宠物包。

### 底栏进度条

- 全片一条 track（非逐场景呼吸条）
- tip = sheet **row 1 running-right** 循环；**每帧一只**狐贴在填充端
- `global_frac` = 全局帧 / 全片总帧

### 右上 showcase

- 尺寸≈字幕卡高（~180）；**右边距≥128**（防小红书裁尾）；无白卡片；边缘 feather 去晕
- **一整行姿态播完**再换行；换哪一行 = 本片 BGM RMS（calm→idle/wait/wave，hot→jump/run/fail）
- hold：calm 36 / mid 24 / hot 14 帧@30fps

### 最终 compose 准入

- 含文字整张信息图禁止 scale-up/crop 或全幅 Ken Burns；动效只进无字插画层；
- 每个章节最终 ffmpeg 抽帧必须生成 `compose-layout-v2`，由 render manifest 自动纳入全部 typography slots，校验最终安全区、脚注与 Astra 碰撞；
- 视频 review 必须以 `--expected-artifact-kind composed_frame` 校验并逐帧绑定 `compose_layout_path`；poster PASS 只算母版资产层，不得放行 publish。
- **禁用** sheet row 1（留给底栏）；禁用写死秒表换姿态

### QA

抽帧确认：右上有狐、底栏一只 tip、狐色=sheet 原色、无白托盘。

## 封面（publish）

Run 内脚本模式（范例 `make_covers.py`）：

1. 必出两套：`cover_xhs_note.png`（笔记风高信息量）+ `cover_douyin_bigtype.png`（高对比大字、数字/绝对主张更大）
2. **主图可轮换**：允许交叉挂载试反应；decision_log / README_covers 记 `xhs_main` / `dy_main`
3. `ffmpeg` 抽 `cover_from_video.png`

输出：`exports/<slug>/{xhs,dy}/covers/`

**成片开场：** 前几秒静图结论/信息图（服务 3 秒留客）；feed 主封可与片头不同、可轮换。DY/XHS 口播第一句都必须钩**观众生活相关性**；禁止作者「翻到研报」暖场。`render_fallback.py` cover_hold 可垫信息图。尾帧再垫 ~0.45s。

外部生图只做无字底图；Gemini prompt 契约见 skill `references/covers.md`。头像只在品牌初始化时生成一次，批准后锁定，不随每期重抽；prompt 见 `references/production-defaults.md`。

## 发布正文（publish）

强制 skill `design-report-explainer/references/caption-body.md`：

1. 几句说清视频是什么（3 秒判断）
2. 正文自然语言命中 2–3 领域关键词（搜索；不只靠 #）
3. 结尾互动问：小红书 **开放思考型** / B站竖屏 **开放争议·辩论型**

## 竖屏图表

scene_plan / render：KPI、对照、时间轴 **上下堆叠**；字幕偏上（XHS）；禁生产备注进 UI。

## Dark Gallery 变体（2026-08-05）

- 路由：CEO 点名或严肃研报向选题自决选用；规范 = `styles/dark-gallery.yaml`（含 `explainer_addendum`），skill 侧条款见 `design-report-explainer` SKILL「Dark Gallery 变体」。
- **Astra chrome 整套关闭**（上文 Astra 节本变体不适用）：白色极简进度条 + 顶部展签 + 底部口播同步字幕。
- **assets 零生图**：展品全部确定性灰阶绘制；TTS 锁死参数不变，BGM 换低弦/底噪 0.04 或静默。
- **beat 化强制**：一屏一元素 · 4-8s 一个视觉事件 · 数字整值弹出禁 count-up · 黑场唯一转场。
- 参考成片与 PoC 渲染脚本：`projects/nomura-semi-packaging-emib-20260804/{renders, dark_gallery_poc}/`。

## Director 钩子

| Director | 增量 |
|----------|------|
| research | NotebookLM pillars + quiz_bank + ASR density；复杂 PPT 修复清单 |
| scene_plan | 双平台分镜写完即进资产；最复杂图表列入自检静帧 |
| asset | 直接批量；锁死 voice/speed/bgm_vol；**拷贝 Astra sheet 到 assets/brand** |
| compose | 按规范实现 Astra chrome；竖堆叠；全片进度条；cover_hold；禁止含字全幅 crop/zoom；逐帧 `compose-layout-v2` + composed-frame review；**B站竖屏（dir=`dy`）CBR≈1400kbps → 35–45MB**（须 minrate）；重渲覆盖 `renders/work/<platform>`；**exports/final.mp4 hardlink，禁双份**；包就绪后 GC |
| publish | 双封面可轮换 + cover_from_video；quiz 钉评；**正文三原则**；按需 `reader_bonus` |
