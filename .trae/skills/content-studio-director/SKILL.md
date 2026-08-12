# Content Studio Director Skill

## 触发条件
当 Alan 在 OpenMontage workspace 中请求内容状态查看、Sceneplan Gate 审阅、异步重生、视觉 QA、Prime 恢复或 receipt 查询时触发。普通编码任务不触发。

## 命令清单

### 只读命令（read-only）
- `current` — 显示当前项目状态：阶段、status、awaiting_human
- `status --project-id <id>` — 项目完整状态含 Sceneplan Gate + Prime resume receipt
- `show-gate --project-id <id>` — 打开 Sceneplan Gate：显示 cuts、contact sheet、continuity
- `job-status --job-id <id>` — 查询异步 job 状态
- `context search <query>` — 检索 OpenViking 资源/知识/goodcase
- `media search <query>` — 检索 Qdrant 素材库（14,133 points）
- `context health` — OpenViking + Qdrant 健康检查

### 提交命令（submit-job）
- `submit-continuity-regen --project-id <id>` — 按 VCP 异步重生，5 秒内返回 ACCEPTED + job_id
- `build-review-packet --project-id <id>` — 构建 review packet（contact sheet + manifest + images）

### 人工写入命令（human-write）
- `apply-sceneplan --expected-checkpoint-sha256 ... --decisions-json ...` — 应用 Alan 的 cut decisions
- `open-prime --project-id <id>` — 从 Trae terminal 打开 Direct Prime（项目绑定 session）

## 使用约束
- 优先调用固定 CLI，不现场拼 Python/PowerShell。
- provider/model 从项目配置读取，不写死在 prompt 中。
- 只引用 repo-relative 文件路径。
- VISUAL_QA 必须基于真实图片输入，输出统一 schema。
- 失败返回 receipt，可重试，不要求 Alan 重贴上下文。