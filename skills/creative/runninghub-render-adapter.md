# RunningHub render adapter — Studio overlay

Local Windows is the director system + cheap draft. RunningHub is a **cloud
render factory**. OpenMontage stays the only production ledger.

```text
Creative Intent  →  SHOT_RENDER_PACKAGE_v1  →  Provider Compiler
```

Not:

```text
Creative Intent  →  a RunningHub prompt pasted into the website
```

## Role

This overlay **packages and quotes**. It does not direct shots and does not
let Cursor impersonate Prime.

Do not call `dispatch_cut` / `produce_keyframe` / `compose_scene`.
Do not add Xiaoyunque or LibTV HTTP clients here.

## What was added

### 1. `SHOT_RENDER_PACKAGE_v1`

Schema: `schemas/artifacts/shot_render_package.schema.json`
Pack: `lib/shot_render_package.py`

`frames.first_frame.kind` is explicit. `IDENTITY_REFERENCE` cannot be Picture 1.
Empty `SHOT_KEYFRAME` (no pixels) is illegal. A 16:9 MCU copy is
`DIRECTED_MCU_COPY`, not a 9:16 shot keyframe.

### 2. `render` on ShotContract (`scene_plan.scenes[]`)

`target` / `stage` / `profile` are **routing hints**. They do not authorize
`dispatch_cut`. PERFORMANCE still compiles to local H3 unless Prime later
opens an external submit.

Allowed targets: `local_h3`, `local_deterministic`, `runninghub`,
`xiaoyunque`, `libtv`.

`compile_provider(..., "xiaoyunque")` and `"libtv"` **raise**. Teacher and
lab stay outside this adapter.

### 3. RunningHub Workflow API

`lib/runninghub_adapter.py` + `profiles/runninghub/rh_h3_fl2va_final_v1.yaml`

Official: upload, `POST /task/openapi/create`, poll `/task/openapi/outputs`.
Host default `www.runninghub.ai`. Key: `RUNNINGHUB_API_KEY`. Optional
`RUNNINGHUB_WORKFLOW_ID`.

Quote always `requires_confirm: true`, `coins_unknown: true`.
Submit without confirm is refused.

Workflow API can use Consumer-Member keys. Model API / LLM need
Enterprise-Shared. Do not assume the website sub covers every endpoint.

### 4. Receipt / Observation / REVIEW_QUEUE

`OUTPUT_RECEIVED` is not OM PASS and not `FIRST_TAKE_ACCEPTABLE`.
Human still picks A/B/NEITHER then CONTINUE/REVISE/SHIP.

## Sandbox command

```text
cd C:\ContentStudio\repos\OpenMontage
$env:PYTHONPATH = "C:\ContentStudio\repos\OpenMontage"
python tools\runninghub_sandbox.py package
```

`--submit` stays disabled on `package` / `quote`. RH-001 uses
`python tools/runninghub_sandbox.py lifecycle` (quote) or `lifecycle --submit`
after Alan clones FL2VA, exports API JSON, fills `workflow_id`,
`workflow_api_json_sha256`, bindings, and sets `RUNNINGHUB_API_KEY`.

Hash mismatch FAIL CLOSED (UI save can retarget nodeIds).

Upload `fileName` is a provider external handle on the receipt, next to
`source_sha256`. Not an OM registry. Receipt `auth_profile` is
`runninghub_default`. Never persist the API key. `usage.rh_coins` stays
null unless the API (or a later human UI fill) actually reports it.

OUTPUT_RECEIVED is not QUALITY_PASS. Same Observation / REVIEW_QUEUE as local.

Explore JSON ≠ callable `workflowId`. See `research/VIDEO_WORKFLOW_TEACHERS/RH-001.md`.

## Lifecycle OM recognizes

```text
PACKAGE → SUBMIT → WAIT → RECEIVE → OBSERVE → REVIEW
```

Xiaoyunque: PACKAGE → EXPORT bundle → AWAITING_OPERATOR_SUBMIT (not this file).
LibTV: PACKAGE → canvas preflight (not this file).
