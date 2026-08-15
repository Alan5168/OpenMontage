---
name: content-studio-director
description: >
  Windows Content Studio 导演入口。仅在 Alan 要看当前 Gate、提交异步重生、
  审 review packet / 真图、写入 cut decisions、或从 Trae 终端 attach Direct Prime
  时使用。普通编码、重构、新 pipeline、MCP 安装不要触发本 skill。
---

# Content Studio Director

OM 是 Studio。本 skill 只是跟工头讲话的入口，不是制作监看 GUI。
看板：`python tools/content_studio_gateway.py --project-id <id> board`
或 Backlot `/p/<id>`。长任务用 Prime Agent TUI，不要把 DSH 搬来 Windows。

只调用下面固定 CLI。禁止现场拼 Python / PowerShell。禁止写 checkpoint / PASS。

工作目录必须是本 OpenMontage 仓库。`--project-id` 从 Alan 或 `current` 输出读取，不要猜。

## 只读

```text
python tools/content_studio_gateway.py --project-id <id> current
python tools/content_studio_gateway.py --project-id <id> show-gate
python tools/content_studio_gateway.py --project-id <id> status
python tools/content_studio_async_console.py --project-id <id> job-status --job-id <job>
python tools/om_context_bridge.py search "<query>" --top-k 5
```

## 提交异步 job（≤5s 返回）

```text
python tools/content_studio_async_console.py --project-id <id> submit-continuity-regen
python tools/content_studio_async_console.py --project-id <id> build-review-packet
```

未获 Alan 当场授权，不要提交 H3 / render / publish。
`board` 里 `department=planning` 的 cut 还没有过审静帧，图上走不到 render。

## 看图 / Visual QA

必须打开真实图片，不能只读 JSON。

```text
python tools/visual_qa.py --project-id <id> --image-dir <review_packet/images>
```

## 写入 Alan 决定（human-write）

先 `show-gate` 取 `checkpoint_sha256`，再：

```text
python tools/content_studio_gateway.py --project-id <id> apply-sceneplan --expected-checkpoint-sha256 <sha> --decisions-json "<json>"
```

`decisions-json` 只能是 Alan 给出的 keep/change/merge/omit。Agent 不得代批。

人锁 identity（master sheet；不批准每镜，不开 H3）：

```text
python tools/content_studio_gateway.py --project-id <id> lock-visuals --i-am-human --master-sheet <png>
```

## Direct Prime（T5）

在 **Trae 集成终端**（不是 Pi、不是 Cursor）执行：

```text
python tools/run_content_studio_prime_chat.py --project-id pilot-ai-content-os-state-machine-zh-v1
```

等价：`python tools/content_studio_async_console.py --project-id <id> open-prime`

成功 resume 后，由 Alan 在 `C:\ContentStudio\reports\windows-trae-native-content-harness-v1\T5_TRAE_ATTACH.json` 写收据（见 `fixtures/t5_trae_attach.example.json`）。没有这张收据，T5 保持 NOT_PROVEN。

## 失败

同一命令失败三次停止，报告 root cause。结束写 receipt，不改本 skill、不接 MCP。
