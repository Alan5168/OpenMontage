# Content Studio Project Memory (Windows-local)

## Alan 交互偏好
- 主要用中文交流。
- 不接受前台等待十几分钟；长任务必须异步，5 秒内返回 job_id。
- 先审内容/关键帧，再授权生产。
- 看图任务必须真实展示图片。

## 架构约束
- Windows Content Studio 独立于 Mac runtime。
- OM 是唯一生产事实源。
- Trae 是 GUI，Prime 是长任务 Harness。
- Bailian Token Plan 优先用于 Wan 多模态生成。
- 不保存 secret、会话全文、路径清单、项目状态、临时错误。