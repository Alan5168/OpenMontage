# OM Prime Adapter contract

Status: repo-local Prime Python skill. Load only with `--skill integrations/prime-om-adapter`. Do not install into `~/.prime/agent/skills` or any global skill directory.

## Authority

| Surface | Owner | Adapter may |
|---|---|---|
| job manifest / checkpoint / artifact | OpenMontage | read; write only through `lib.checkpoint.write_checkpoint` + artifact schema |
| Prime session / IPython variables | Prime | hold handles, hashes, reload functions |
| human Gate | Windows Pi | `get_gate` yes; `submit_gate_decision` always denied for Prime |
| media / H3 / TTS / publish | OM providers | never call from this skill |

## Actions

- `open_job(job_id)` — read-only refs + hashes
- `load_stage_pack(job_id, stage)` — path/hash/slice; `include_body` defaults false
- `query_casebook(query, scenario_id, error_class=None)` — accepted/rejected file recall
- `submit_stage_artifact(...)` — schema + transition validator; denies assets/edit/compose/publish and Pi-gated stages
- `record_lesson_candidate(...)` — job-local JSONL only, `promoted_to_global=false`
- `get_gate(job_id)` — read-only
- `submit_gate_decision(...)` — Pi only; adapter refuses even if caller claims Pi
- `resume_prime(job_id, session_id)` — write session pointer/receipt; does not change Gate
- `build_context_variables` / `reload_context` / `slice_variable` / `mark_stale`

## Security

- Authorized root: `C:\ContentStudio` or `OM_PRIME_ADAPTER_ROOT`
- Job ids cannot contain path separators
- Secret-like keys/values fail closed
- Binary/media payloads fail closed; store path+hash only
- No second project state file outside OM

## Tests

`pytest tests/tools/test_prime_om_adapter.py -q`
