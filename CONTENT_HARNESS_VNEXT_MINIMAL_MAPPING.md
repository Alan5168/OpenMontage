# Content Harness vNext — minimal mapping

Windows Studio. OpenMontage remains production truth. This file is a mapping, not APPROVED, not a new OS.

Read: scene_plan, shot records, creative loop, LEARNING_EVENT, temporal Observation, H3 IR, Human checkpoint/preference. Then stop.

Steel already locked (do not recant):

- Scene A is corpus, not a demo to finish. Do not polish A4.
- Cursor is harness engineer, not production foreman. Production entry is Windows Prime TUI.
- `PERFORMANCE` / `INTERACTION` cannot compile onto `LIMITED` / `local_compose`. H3 FL2VA is default **for those obligations only**, not for HUD / EST / declared hold.
- Mapping prompt §11 (“H3 is not the default renderer”) means: not all shots. It does not undo H3-first for character performance.
- Policy/Prime must not masquerade as Sensor.

Three proxy failures already observed (same root: measuring a proxy, then treating the proxy as the goal):

1. MP4 container ≠ animation
2. pixel motion ≠ performance
3. perspective-correct bbox ≠ physically valid placement

---

## A. What existing OM objects already carry

| vNext name | Existing OM object | What it already does | Gap |
|---|---|---|---|
| SceneIntent | `scene_plan` + `SCENE_STATE.json` + `creative_intent_contract` | Ordered cuts, visual_intent, duration, identity lock | No `audience_state_change`. Intent is “what is on screen”, not “what the audience now knows”. |
| ShotContract | `scene_plan.scenes[]` | `animation_class`, `visual_intent`, `shot_intent`, `character_ids`, `character_variant`, `start_frame_ref`, `motion_route`, additive `motion_obligation` / `performance_intent` / `intentional_hold` / `renderer` | Frozen/free/legal_repairs not first-class. `observable_acceptance` is prose at best. |
| ContentIR | `lib/h3_context_ir.py` `compile_h3_ir` | Shot-level compiler: identity, shots[], camera, audio, avoid, first/last frame, duration 4–15s, FL2VA/I2VA/R2VA. Does not PASS. | This is **H3 prompt IR**, not scene ContentIR. No frozen/free split, no audience_state_change, no observable_acceptance. |
| WorldState | job `SCENE_STATE.json`, `JOB_SKELETON.json`, `HOUSE_RULES`, bible paths | Canonical identity, ship flags, corpus role | Not a per-shot world lock. Kitchen identity is a JPEG path, not a location asset. |
| Rollout | ad-hoc receipts (`A4_*_RECEIPT.json`, `COMPOSE_V5_RECEIPT.json`), `cost_log`, `render_report` | Some provider/model/output path | No rollout id, no ContentIR hash, no input asset hashes, no parent/repair origin. H3 takes are filenames (`A5_sage_fl2va.mp4`). |
| Observation | `temporal_motion_report`, `frame_packet`, `audio_event_map`, `limited_grammar_report`, `overlay_preflight`, `layout_geometry` report | Dense 8fps MAD; hash-bound frames; loudness windows; overlay L0; VP/height | Motion types are **global MAD classes**, not camera vs graphic vs ambient vs prop vs character vs performance. `motion_coverage` is a proxy. Geometry has no support surface. |
| Eligibility | `scene_eligibility` | Cheap previz vs film; ken-burns / reuse / first-sound / placeholder | **Harness bug on Scene A v5:** `director_review_eligible=true` while A4 stood on a table and character performance was unseparated from FX. `requires_performance` only trips if overlapping segments are *all* STATIC/CAMERA. Steam/HUD/loop counts as LIMITED_LOCAL → not a blocker. |
| Critique | `editorial_critique` | Must cite timestamps + frame ids + intent_id; hash must match mp4; generic text banned | Illegal without temporal SEE + eligibility. That coupling is right. Critic still cannot APPROVE. |
| RepairAction | `repair_plan` + `patch_receipt` | Segment-scoped actions | No enumerated legal_repairs (prompt / ref / frames / provider / split / abandon). Unlimited retry not blocked in schema. |
| HumanPreference | `decision_log.user_approved`, `review.findings[].disposition`, human-only graph edges (`APPROVED`) | Alan can approve; agents cannot write APPROVED | No A/B/NEITHER/KEEP_WATCHING/STOP labels pointing at a rollout. Alan is still pulled into QA. |
| LearningEvent | `schemas/artifacts/learning_event.schema.json` + job `working/learning/le-*.json` | Land-to-casebook; v0.1 `auto_retrieve` must be false | Job files already violate schema (`locked`, `supersedes`, `auto_retrieve: true`, too many `hard`). Promotion ladder (candidate → prior → hard_candidate) does not exist. |
| Location surface | none | `layout_geometry_check` answers height at a footpoint | **Root cause 1.** No walkable polygon. Caller could stamp `surface=floor_tile`. Brightness ≠ floor. |

Policy vs Sensor (do not merge):

| Role | May answer | Must not |
|---|---|---|
| Prime / Policy | I want Avery here | This pixel is floor |
| Sensor | What surface is this? What moved? | Whether the shot is good |
| Geometry function | Legal height at this foot, if walkable | Approve layout |
| SEE | Did the declared temporal beat happen? | Director taste |
| Critic | Does Observation serve ContentIR? | APPROVE / rewrite OM truth |

---

## B. Smallest missing fields (additive, do not rename)

Do not invent parallel entities. Add onto existing artifacts.

### On `scene_plan.scenes[]` (ShotContract)

Already added this session: `motion_obligation`, `performance_intent`, `intentional_hold`, `renderer`, `character_variant` (phase × costume × view; `still_refs` are IDENTITY_REFERENCE, never SHOT_KEYFRAME).

Still missing, keep tiny:

- `audience_state_change` (string, 1–2 sentences)
- `frozen` (string[] or short object: identity, costume, prop, start/end)
- `free` (string[])
- `observable_acceptance` (string[]; must be sensor-checkable)
- `legal_repairs` (enum list)
- `temporal_beats[]`: `{kind: HOLD\|CAMERA\|AMBIENT\|CHARACTER_PERFORMANCE, t_start, t_end}` — this is temporal intent truth, not motion_coverage

### On Observation (extend `temporal_motion_report` later, do not rewrite SEE now)

Need split fields, not a new report type:

- `camera_motion`
- `graphic_motion` (HUD/scanline)
- `ambient_fx_motion` (steam/fire)
- `prop_motion`
- `character_motion`
- `character_performance_motion`

Plus `temporal_intent_realization`: per declared beat PASS/FAIL against those splits.

**Do not use `motion_coverage` as eligibility.** Keep it as a measurement footnote.

### On Eligibility

Must AND:

1. Layout legally placed (support surface + height), if a character is claimed on a ground plane
2. Declared temporal beats realized

v5 `director_review_eligible=true` is **FALSE_DIRECTOR_ELIGIBILITY_01**. Expected: NOT eligible. Do not offer Alan that master.

### On Rollout (new *optional* sidecar, not a schema rewrite)

For **new** H3 / image / major compose only:

`rollout_id`, `shot_id`, `content_ir_hash`, `provider`, `model`, `mode`, `input_hashes[]`, `output_path`, `parent_rollout_id`

Map onto existing receipt JSON + `cost_log.entries`. Do not migrate old takes.

### On LEARNING_EVENT

Schema today: `constraint_class` ∈ {hard, prior, explore}, `auto_retrieve` const false, `human_accept` ∈ {pending, accept, reject}.

Job events already drifted. Next additive enum values (later, with tests): `candidate` as default for one failure. Do not hard aesthetic lessons. Keep hash/contract/geometry-impossible as hard.

### On HumanPreference

Additive artifact or `decision_log.category` value: `human_preference` with `label` ∈ A/B/NEITHER/KEEP_WATCHING/STOP/CONTINUE_SCENE/ABANDON_SCENE/SHIP/DO_NOT_SHIP, `target_rollout` or `target_scene`. Do not auto-promote to hard rule.

### On location (root cause 1)

Not a new Agent. A **location production asset** next to the BG, e.g. `bible/avery/approved/backkitchen_wide.surfaces.json`:

walkable_floor / non_walkable / vertical_surface / occluders / horizon / VP

`layout_geometry_check` must **read that map** or return `UNKNOWN`. It must not accept caller `surface=floor_tile` as fact.

Do not MoGe every shot. Build the map once for this kitchen. Exception sensor stays exception sensor.

---

## C. What is additive (safe next)

- Keep `motion_obligation` compile fail (already in `lib/motion_obligation.py`, 23 tests green).
- Name Scene A corpus cases, including FALSE_DIRECTOR_ELIGIBILITY_01.
- ContentIR as a **view** over `scene_plan.scenes[]` + `h3_ir` spec, not a second ledger.
- Rollout sidecar on new generates.
- Surface map JSON for `backkitchen_wide` when Alan greenlights that knife.
- Eligibility: require `requires_performance` **or** `motion_obligation=PERFORMANCE` to check character_performance_motion, and never treat LIMITED_LOCAL FX as performance.
- Learning: default new events to explore/candidate; stop stamping `hard` on taste.

---

## D. What would break canonical truth (do not do now)

- Rewriting `temporal_motion_report` v0.1 in place (breaks Scene A SEE files and tests).
- Making `scene_eligibility` fail every STATIC_HOLD (kills legal 止め絵).
- Auto-upgrading LIMITED → H3 without a declared PERFORMANCE obligation.
- Letting Prime `/refine` write OM canonical state or “Avery is 24%”.
- Promoting job `le-*.json` with `auto_retrieve: true` into the schema-true LEARNING_EVENT writer.
- Pixel-locking every shot to `backkitchen_wide.jpg`.
- A third memory manager / Hindsight / wiki.
- Cursor remaining in the production graph.

---

## E. Defer until 10–20 real scenes

- Platform Council / Retention Agent
- Visual Critic farm
- Episode automation
- Migrating all old assets to IR
- Qwen-MM as a Sensor (interface only)
- Auto `/refine`
- Full occlusion-aware depth ordering in geometry
- KPI dashboard (Alan minutes / publishable minute) as a product
- Held-out promotion to `hard_candidate`

---

## F. Scene A artifacts as first samples

| Bench id | Fixture | Expected observation | Counterexample (must not false-fail) |
|---|---|---|---|
| sparse frames as animation | pre-honesty v4 scrap; `le-20260815-see-without-temporal-evidence` | NOT video | Intentional hold with declared NONE |
| overlay orphan / clip | overlay L0 tests | compile/block | Legal HUD that changes measurably (A1) |
| wide → MCU paste | `A4_seedream_layout.jpg`, `A4_qwen_leftcrop.jpg` | not EST | Shot-specific new BG of same kitchen |
| silence / BGM covers VO | early mixes before `mix_30.wav` | first_sound late | Mix with first_sound=0, VO present |
| H3 smile / end-frame drift | Hailuo A5 takes; contrast `A5_sage_fl2va.mp4` | identity/mouth drift | Locked-off FL2VA, mouth closed |
| **FALSE_DIRECTOR_ELIGIBILITY_01** | `scene_a_master_v5.mp4` + `see/scene_eligibility.json` (`eligible=true`, coverage 0.5858, A4 on table then aisle salvage, A4 STATIC_HOLD, steam/HUD as LIMITED_LOCAL) | **NOT_DIRECTOR_ELIGIBLE** | A5/A6 FL2VA as isolated PERFORMANCE cuts with matching intent |
| support ≠ floor | `A4_b_composite_on_table.jpg`; lock `(0.22,0.70)` | foot not walkable | Aisle tiles ~x=0.41 at same depth |
| self-confirmation | Agent wrote floor → geometry pass → layout bar pass → eligible | Policy≠Sensor | Independent surface map UNKNOWN/FAIL |

Creative intent contract analogue already in OM: `must_convey` ≈ frozen, `creative_freedom` ≈ free. Too weak for observable_acceptance. Reuse the names; do not fork.

H3 FL2VA success sample: `assets/video/scene_a_h3/A5_sage_fl2va.mp4` (~5s, local 5070 Ti). That is the motion department working **after** a keyframe, not a reason to H3 HUD.

---

## Layout geometry (keep narrow)

Keep `lib/layout_geometry.py` as a Function. It does not APPROVE. After a location surface map exists, it must verify walkable or return UNKNOWN. Height-without-depth remains a valid diagnostic (left-front + 22% is illegal). That knowledge is done. Do not run MoGe on every cut.

If a character must walk: that is PERFORMANCE, keyframes + H3, not a static A4 LIMITED religion.

Director options for a *future* kitchen EST (not this session): B2 aisle-left walkable foot, or C empty EST → MCU. Not more image-edit into a frozen JPEG.

---

## Prime `/refine` slot (interface only)

May update: “for this pattern, try this strategy first.” Must cite evidence, min diff, rollback, one counterexample. Must not write OM canonical state. Do not start auto-refine.

---

## Do not merge short-drama factories

Moyin-creator, StarReel MCP, and ArcReel stay **outside** this tree. Absorb only:

- `character_variant` on ShotContract (wardrobe on the cut, not in `world_lock`)
- composition-bound SHOT_KEYFRAME before H3 (already `first_frame_readiness`)
- Seedance ≤9 ref packer + `quote_only` (`lib/seedance_ref_packer.py`, `lib/metered_provider.py`)
- H3 capability map (`lib/h3_capability_map.py`): ship = FL2VA NVFP4 20-step. Turbo/Ref2VA are candidates, not ship. Isolated sandbox: `jobs/h3-capability-sandbox-v1`.
- `SHOT_RENDER_PACKAGE_v1` + `scenes[].render.target` + RunningHub Workflow API adapter (`lib/shot_render_package.py`, `lib/runninghub_adapter.py`). Quote-before-submit. Xiaoyunque/LibTV are routing enums only (teacher / lab). Overlay: `skills/creative/runninghub-render-adapter.md`.

Do not install MCP clients. Do not vendor AGPL workstations. Do not let Cursor `dispatch_cut`. Overlay: `skills/creative/short-drama-factory-adapters.md`.

---

## Stop

No new Agent, no schema rewrite, no SEE rewrite, no A4 generate, no surface map implementation in this file’s wake until Alan picks the next knife.

Suggested next knife after this mapping (Alan chooses one):

1. Eligibility + temporal_intent_realization so FALSE_DIRECTOR_ELIGIBILITY_01 fails closed (Observation truth).
2. One location surface map for `backkitchen_wide` so geometry cannot be fed `floor_tile` (Sensor truth).
3. Prime TUI `open_job` → `compile_cut` path so Cursor leaves the production graph.
