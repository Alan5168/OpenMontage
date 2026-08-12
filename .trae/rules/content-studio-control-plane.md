# Content Studio Control Plane

## 交互约束
- 中文短答；先给状态与下一步，不展示长推理。
- "打开/看看/审一下"默认只读，不改 canonical 文件。
- "重生/生成"默认只提交异步 OM job，5 秒内返回 job_id。
- canonical artifact/checkpoint 只能经固定 OM gateway/console 写。
- 未获得 Alan 明确 cut decisions（keep/change/merge/omit），不得 approve。
- 看图任务必须实际打开/附加图片，不能只读 prompt/JSON 后声称看过。
- 不调用 H3/render/publish，除非 Alan 在该次任务明确授权。
- 不读取或输出 key/token/auth 内容。
- 同一根因失败三次停止并报告 root cause。
- 结束写 receipt，不自动扩充规则。

## 职责边界
- OM 是唯一 project state 事实源。
- Trae 是 GUI 入口，不临时写生产脚本。
- Prime 是长任务 Harness，不伪造 Gate。
- Qdrant 是素材专用检索，不反写 OM state。
- OpenViking 是上下文导航，不自动提交 session。