# OM Prime Adapter contract

Status: repo-local Prime Python skill. Load only with `--skill integrations/prime-om-adapter`. Do not install into `~/.prime/agent/skills` or any global skill directory.

## Authority

| Surface | Owner | Adapter may |
|---|---|---|
| job manifest / checkpoint / artifact | OpenMontage | read; write only through `lib.checkpoint.write_checkpoint` + artifact schema |
| Prime session / IPython variables | Prime | hold handles, hashes, reload functions |
| human Gate | Windows Pi | `get_gate` yes; `submit_gate_decision` always denied for Prime |
| media / H3 / TTS / publish | OM providers | Prime requests `dispatch_cut`; OM authorizes and invokes providers. Prime cannot set `generate=true`. `compile_cut` remains proposal-only. |

## Actions

- `open_job(job_id)` — OM canonical world: scene state, shot contracts, identity pointers, blockers, observations, rollout receipts, OpenViking pointers if present (never invented), human lock, `next_step` (revise job: REVISE is not terminal; lights-out walks S1–S4 then compose and is frozen)
- `submit_scene_proposal(job_id, proposal)` — Prime only. Intent proposal. Shots illegal until HumanPreference `CONTINUE_SCENE` or, on the revise job, `REVISE`.
- `submit_revision_proposal(job_id, proposal)` — Prime only on `SCENE_REVISE_PROPAGATION_PROOF`. Thin record: `parent_scene_hash`, `review_id`, `affected_shots`, `revision_reason`, `revision_number`. OM rejects S2/H3 in affected_shots. Cursor cannot.
- `record_human_preference(job_id, label)` — Alan/Pi only (`CONTINUE_SCENE` / `STOP` / `REVISE` / scene-level `KEEP_WATCHING` / `SHIP` / `DO_NOT_SHIP`). Prime cannot forge it.
- `get_human_preference(job_id)` — read-only
- `compile_cut(job_id, shot_id)` — Prime only. Writes `working/prime_rlm/execution_requests/<shot_id>.json`. PERFORMANCE → H3 FL2VA; INTERACTION prefers `h3_ref2va` and COMPILE FAILs `R2VA_RUNTIME_UNAVAILABLE` until Ref2VA weights/workflow exist (no FL2VA fake); NONE/LOCAL → existing deterministic path. `generate=false`. New-scene shots require CONTINUE_SCENE or REVISE on the revise job.
- `dispatch_cut(job_id, shot_id)` — Prime only. Accepts an existing Prime `PROPOSAL` with `generate=false`. PERFORMANCE → H3 FL2VA. NONE/LOCAL → ffmpeg still-hold / local_compose + RECEIPT + SEE. vid3 `scene_b`/`B2` freeze-on-success stays that knife only. Lights-out does not freeze after one PERFORMANCE rollout. Revision dispatch requires REVISE and only affected shots; unchanged/H3 stay on parent hashes. No automatic retry. Prime cannot flip `generate`. Cursor cannot impersonate Prime.
- `compose_scene(job_id)` — Prime only. Concat S1–S4 mp4s, hash, SEE on composed output, write `working/prime_rlm/REVIEW_QUEUE.json`. On the revise job, writes `scene_v2.mp4` with `parent_scene_hash`. Scene-level review, not per-cut A/B. Does not stamp `LIGHTS_OUT_SCENE_PRODUCTION_PROVEN`. Cursor cannot compose.
- `submit_prerequisite_plan(job_id)` — Prime only. Turns a blocked B2 receipt into a dependency plan: Lucien identity → B1 NONE keyframe → B2.start_frame_ref. Does not retry H3.
- `propose_identity_candidates(job_id)` — Prime only. A/B Lucien plates. Human `A`/`B`/`NEITHER` on `identity:lucien_mercer`. Does not replace Avery.
- `produce_keyframe(job_id, B1)` — Prime only after Lucien is locked. NONE still. Binds as B2.start_frame_ref. Not H3.
- `load_stage_pack(job_id, stage)` — path/hash/slice; `include_body` defaults false
- `query_casebook(query, scenario_id, error_class=None)` — accepted/rejected file recall
- `submit_stage_artifact(...)` — schema + transition validator; denies assets/edit/compose/publish and Pi-gated stages
- `record_lesson_candidate(...)` — job-local JSONL only, `promoted_to_global=false`
- `get_gate(job_id)` — read-only
- `submit_gate_decision(...)` — Pi only; adapter refuses even if caller claims Pi
- `resume_prime(job_id, session_id)` — write session pointer/receipt; does not change Gate
- `build_context_variables` / `reload_context` / `slice_variable` / `mark_stale`
- `openviking_health()` / `search_openviking(...)` / `read_openviking(uri)` — read-only access to shared OpenViking context; these functions never write OM state or OpenViking memory

## Security

- Authorized root: `C:\ContentStudio` or `OM_PRIME_ADAPTER_ROOT`
- Job ids cannot contain path separators
- Secret-like keys/values fail closed
- Binary/media payloads fail closed; store path+hash only
- No second project state file outside OM

## Tests

`pytest tests/tools/test_prime_om_adapter.py tests/tools/test_prime_production_entry.py tests/lib/test_motion_obligation.py -q`

Production TUI: `python tools/run_prime_production_tui.py --project-id <job_id> --command open_job`
