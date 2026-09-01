---
name: end-task-studio
description: >-
  Close or pause a Windows Content Studio task with an OpenMontage job writeback,
  optional LEARNING_EVENT candidates, and a verified cross-frontend OpenViking hot
  handoff. Use for end task, session handoff, 保存记忆, 收口, or 记录断点 on Windows.
---

# End Task — Windows Content Studio

Windows uses OpenMontage for production truth and one bounded OpenViking hot index
for cross-frontend handoff. Do not create a Mac-style wiki, mem0, or Hindsight layer.

## Required closeout

1. Write or update the job's `SESSION_WRITEBACK_YYYYMMDD.md`. Keep full evidence,
   decisions, blockers, and next steps there.
2. If a reusable failure or rule was observed, write an OM `LEARNING_EVENT` under
   the job's `working/learning/` and copy it to OV `casebook/candidates/`. It remains
   a candidate until an OM receipt says `PROMOTE` and regression passed.
3. Upsert the current handoff into the shared hot index with the canonical script:

```powershell
python <skill-root>\scripts\end_task.py upsert `
  --task "H3 capability sandbox" `
  --job-id "h3-capability-sandbox-v1" `
  --lane "content-capability" `
  --status "WAITING_HUMAN" `
  --summary "PDD rejected; RH-001 remains quote-only" `
  --gate "RH-001_WORKFLOW_API_JSON_REQUIRED" `
  --next-action "Alan exports the cloned Workflow API JSON" `
  --source-writeback "C:\ContentStudio\jobs\h3-capability-sandbox-v1\working\SESSION_WRITEBACK_20260901.md" `
  --saved-by "cursor" `
  --set-focus
```

Use `--decision` and `--pointer` repeatedly when needed. Use `close --job-id ...`
only when the task is actually closed. The script migrates the legacy singleton,
locks concurrent writers, performs an atomic upsert by `job_id`, syncs the complete
index to OpenViking, and reads it back by hash.

## Completion claim

An end-task is complete only when the script exits `0` and prints:

```text
status: PASS_HOT_WRITE
hot_write.ov_verified: true
```

Otherwise report `PARTIAL_HOT_SYNC_FAILED` and give the local file plus error. Do
not claim cross-frontend handoff from a model-authored `resumed=true` or from an OV
research pointer.

## Memory boundaries

- `current_task_context.json` is a small multi-job index, not a transcript. Never
  append raw chat and never replace unrelated jobs.
- Full detail belongs in the job writeback. Hot entries contain only the latest
  summary, gate, next action, and pointers.
- OM `LEARNING_EVENT` is not hot memory. OV `resources/.../research` is not hot
  memory. OV `preferences` is for stable human preferences, never task handoffs.
- Do not install or write Mac `memory-md`, wiki, mem0, Hindsight, or `00_hq` here.
- Do not promote lessons without an OM promotion receipt.

## Resume

Read `viking://user/alan/memories/hot/current_task_context.json`, select the
requested `job_id` or `focus_job_id`, then follow its `source_writeback` and OM job
state. Do not assume the globally latest timestamp is the user's intended task.

