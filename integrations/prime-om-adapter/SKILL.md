---
name: om-prime-adapter
description: >
  Project-local OpenMontage adapter for Prime IPython. Use when a Content Studio
  job must be opened, a next-scene proposal submitted, compiled, sliced, or
  resumed without a second project state. compile_cut writes a proposal only.
  dispatch_cut requests OM-owned execution of an existing Prime PROPOSAL.
  HumanPreference is Alan/Pi only. Cursor is not the production foreman.
---

# OM Prime Adapter

Call from the Prime Agent IPython kernel. Do not paste media, credentials, or
whole artifacts into the prompt.

Identity stills use available txt2img APIs first (Volcengine Seedream / DashScope),
not a Flux2-only ComfyUI path. Local Flux2 is optional.

Human console is `studio` at `C:\ContentStudio` (`studio status`, `studio continue`, `studio run`). It reads OM `next_step` and launches the existing foreman session. It does not dispatch. Prime TUI remains the debug surface.

```text
python tools/run_prime_foreman_session.py --scene-revise --project-id vid-scene-revise-v1
```

Lights-out execution is frozen. `vid-scene-revise-v1` is frozen: `SCENE_REVISION_ROUTING_PROVEN`, effectiveness unproven. Do not polish. Do not stamp `SCENE_REVISION_EFFECTIVENESS_PROVEN`. Cursor does not generate.

If the primary reasoning provider hangs before IPython, the same Prime RPC process
aborts that turn and switches to the next configured model. Cursor does not call
OM production actions on Prime's behalf.

```python
import om_prime_adapter
job = om_prime_adapter.open_job("vid3-blacklisted-chef-90s-v1")
job["next_step"]
om_prime_adapter.submit_scene_proposal(job["job_id"], {
    "scene_id": "<not scene_a>",
    "audience_state_change": "...",
    "visual_intent": "...",
    "duration_target": "...",
}, caller="prime")
```

Do not split cuts until Alan records `CONTINUE_SCENE`.
Do not generate. Do not polish Scene A. Do not call `submit_gate_decision`.
Prime cannot call `record_human_preference`.

`PERFORMANCE → H3 FL2VA`. `INTERACTION → preferred h3_ref2va`; compile blocks with `R2VA_RUNTIME_UNAVAILABLE` until Ref2VA unet + R2V workflow exist. Do not dispatch INTERACTION through FL2VA. `NONE/LOCAL → local_compose`.
`PERFORMANCE + local_compose` is COMPILE FAIL.

`dispatch_cut` is OM-owned execution of an existing Prime PROPOSAL. PERFORMANCE → H3. NONE/LOCAL → ffmpeg still-hold / local_compose. vid3 `scene_b`/`B2` remains frozen harness-acceptance. Lights-out and showpiece must not freeze on the first mp4. `compose_scene` concatenates a finished scene onto a scene-level REVIEW_QUEUE. Do not pass `generate=True`. Do not auto-retry. Readable keyframe required for PERFORMANCE. Cursor cannot dispatch or compose.

If `PRIME_AGENT_KERNEL_PYTHON` is set, this package must already be installed
into that interpreter. PYTHONPATH alone is not a Prime-kernel guarantee.
