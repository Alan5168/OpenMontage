# Content Studio 控制面

- 中文短答。先给状态和下一步，不展示长推理。
- OpenMontage 是唯一 project state。Trae / Prime / Pi / OpenViking 不得写 PASS、APPROVED、checkpoint。
- 「打开 / 看看 / 审一下」= 只读。
- 「重生 / 生成」= 只提交异步 OM job，5 秒内返回 job_id。
- canonical artifact / checkpoint 只能经 `tools/content_studio_gateway.py` 写。
- 没有 Alan 的明确 cut decisions，不得 approve。
- 看图必须实际打开图片；禁止只读 prompt / JSON 后声称看过。
- 不调用 H3 / render / publish，除非 Alan 在该次任务明确授权。
- 没有过审静帧的 cut 停在 planning；不得调用 video_selector / H3 / compose。
- 不读取、不输出 key / token / auth。禁止接 MCP。
- 同一问题失败三次即停，报告 root cause，不做第四次猜测。
- 结束写 receipt。不自动扩充本规则。
