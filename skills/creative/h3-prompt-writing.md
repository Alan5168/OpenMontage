# H3 Prompt Writing — Studio overlay

Layer 3 (how MiniMax writes H3 prompts) is vendored at
`vendor/minimax-h3/h3-prompt-writing/`. Read `SKILL.md`, then `references/base-en.txt`
(T2VA / I2VA / FL2VA / L2VA) or `references/ref-en.txt` (Ref2VA).

This overlay is **how OpenMontage uses that dialect**. It does not replace MiniMax's
field names.

## Role

```text
ShotContract / scene cut
        ↓
this overlay + lib/h3_context_ir.py
        ↓
MiniMax H3 dialect
        ↓
local H3 (NVFP4) or a later hosted H3 call
```

This skill **translates**. It does **not** direct.

Do not use it to invent anchors, storyboards, shot sizes, or first frames.
Do not use it to decide Seedance vs H3. Those are earlier stages.

## Official three fields (Base)

Emit exactly:

```text
integrated_multimodal_description:
overall_soundscape:
non_diegetic_music:
```

Do not rename them. Do not fold sound into the visual paragraph and drop the
other two fields.

## Modes

| Mode | When | Compiler |
|---|---|---|
| T2VA | text only | three fields, no picture-align header |
| I2VA | first frame | official 0.00s `<Picture 1>` header + three fields |
| FL2VA | first and last | official Picture 1 / Picture 2 align header + three fields |
| L2VA | last frame only | official last-frame align header + three fields |
| Ref2VA | labeled refs | **not** `compile_h3_ir`. Six-section rewrite in `ref-en.txt`. Runtime separately gated by `lib/h3_runtime.py` |

`compile_h3_ir(..., mode="r2va")` raises `R2VA_PROMPT_NOT_IN_BASE_COMPILER` on
purpose. Do not paper over missing Ref2VA weights with an I2VA prompt.

## Hard rules on this machine

- Cursor does not `dispatch_cut` / `produce_keyframe`.
- A character master sheet is not a 9:16 `SHOT_KEYFRAME`.
- Do not VLM-"enhance" an already compiled prompt (A5 smile / push-in).
- Frozen jobs stay frozen. This skill is dialect, not a reason to re-render.

## Reference stills (RWTS-001 H4, experimental)

A reference image is a typed bind, not “please refer to this picture.”
`lib/reference_binding.py` is an **experimental provider dialect**. Emit it
only when `experimental_reference_binding` is set. It is not a global
CHARACTER_IDENTITY production rule. SCENE/PROP lists are unverified.

```text
inherit: face, hair, costume, proportions
do_not_inherit: sheet background, duplicate bodies, panel divisions, pose
```

Identity stills never become `<Picture 1>`. Do not add a ReferenceBinding schema.



## Xiaoyunque teacher month

Protocol: `jobs/manhua-blacklist-chef-xiaoyunque-v1/working/teacher_traces/STUDY_PROTOCOL.md`.

Record `teacher-trace/v0.2`. `earliest_divergence` is a hypothesis. Also store
`downstream_effect`, `human_preference`, `candidate_lesson`, `repeat_count`.
Promote a Skill only after 2–3 repeats **and** one held-out. Round 1 does not
generate video. Do not spend H3 until storyboard/keyframe have a compared trace.

Ref2VA weights are public. This PC has no 16GB Ref2VA runtime. Context-IR stays
hosted. Do not collapse those two facts.
