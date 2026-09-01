# Windows Content Studio end-task v2

`current_task_context.json` is the stable cross-frontend entry point. It is a
bounded index of active handoffs keyed by `job_id`, not an append-only transcript
and not the durable production record.

- OpenMontage job files and `SESSION_WRITEBACK` remain production truth.
- OM `LEARNING_EVENT`s remain unpromoted candidates until validated.
- The hot index stores only current summary, gate, next action, and pointers.
- Writers lock, merge by `job_id`, atomically replace, sync to OpenViking, and
  verify the readback hash.
- Closing a job moves it into a five-entry `recent_closed` window. Full history
  remains in the job and OpenMontage evidence, so the hot file stays small.
- Runtime skill copies for the shared agent root, Cursor, Gemini/Antigravity, Pi,
  Hermes, QoderWork, Qwen Office, and WorkBuddy are generated from
  `.agents/skills/end-task-studio` and must match its recorded SHA-256 hashes.

The deterministic entry point is:

```text
.agents/skills/end-task-studio/scripts/end_task.py
```

The installer is:

```text
.agents/skills/end-task-studio/scripts/install_runtime_copies.py
```
