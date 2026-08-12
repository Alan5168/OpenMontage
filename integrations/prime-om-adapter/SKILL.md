---
name: om-prime-adapter
description: >
  Project-local OpenMontage adapter for Prime IPython. Use when a Content Studio
  job must be opened, sliced, validated, or resumed without building a second
  project state. Read-only by default. Human Gate writes are Pi-only.
---

# OM Prime Adapter

Call from the Prime kernel. Do not paste full media, credentials, or whole
artifacts into the prompt. Keep large context in variables and slice them.

```python
job = await om_prime_adapter.open_job("fixture-prime-rlm-historical")
pack = await om_prime_adapter.load_stage_pack(job["job_id"], "research")
hits = await om_prime_adapter.query_casebook(
    "music covering voice-over",
    scenario_id="comic-nonfiction-short-knowledge-zh",
    error_class="music_covers_vo",
)
ctx = await om_prime_adapter.build_context_variables(job["job_id"])
claim = await om_prime_adapter.slice_variable("claim_table", selector={"index": 0})
```

Write paths go through OpenMontage schema and checkpoint validators. Prime must
not call `submit_gate_decision`; that is Windows Pi only.

```python
await om_prime_adapter.submit_stage_artifact(
    job_id,
    stage="content_architecture",
    artifact_name="content_architecture",
    artifact=candidate,
)
await om_prime_adapter.record_lesson_candidate(job_id, lesson)
await om_prime_adapter.resume_prime(job_id, session_id)
```

Authorized filesystem root is `C:\ContentStudio` unless tests set
`OM_PRIME_ADAPTER_ROOT`. Credentials, cookies, tokens, and binary media never
enter variables, snapshots, or returned payloads.
