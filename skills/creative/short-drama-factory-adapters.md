# Short-drama factory adapters — Studio overlay

Moyin / StarReel / ArcReel are **factories**. OpenMontage stays production truth.
This overlay steals gates and translator layers only. It does not install MCP,
does not merge AGPL trees, and does not let Cursor dispatch.

```text
script → storyboard → frames → video → cut
        is their product.

OM already has those stages as artifacts.
Do not grow a second control plane.
```

## Role

```text
ShotContract
        ↓
character_variant + composition bind + (optional) Seedance packer
        ↓
H3 (local, SHOT_KEYFRAME)  or  Seedance R2V (≤9 refs, quoted)
```

This overlay **translates and gates**. It does **not** direct.

Do not call `dispatch_cut`, `produce_keyframe`, or `compose_scene`.
Do not add `@starreel/mcp`, ArcReel MCP, or moyin-creator into this repo.

## What was absorbed

### 1. `character_variant` on ShotContract (`scene_plan.scenes[]`)

From moyin-style boards and job `CHARACTER_CARDS.json`:
`character_id` + `phase` + `costume` + optional `view` + `still_refs`.

`still_refs` are **IDENTITY_REFERENCE**. They are illegal as `start_frame_ref`
for H3. Compile with `lib/character_variant.py`. Bind from cards with
`resolve_from_character_cards`. Optional experimental dialect:
`lib/reference_binding.py` behind `experimental_reference_binding`. Not policy.

### 2. Composition still must be bound before H3

Already in `lib/shot_director.py` `first_frame_readiness`. Variant stills now
add an extra blocker so a face pack cannot impersonate a 9:16 SHOT_KEYFRAME.

### 3. Seedance ref packer (provider adapter)

`lib/seedance_ref_packer.py` orders SHOT_KEYFRAME first, then composition /
scene / identity stills, and refuses >9 images. Same ceiling as
`tools/video/seedance_video.py`. Packing **never** sets `h3_dispatch_allowed`.

Pass `shot=` into `SeedanceVideo.execute` to pack. Pass `quote_only=true` to
get USD without calling fal.

### 4. Wardrobe is not a world lock

StarReel's dead loop: character look in `visual_lock` / art bible, portraits
follow the profile, sheets follow the lock, gate rejects forever.

OM mapping: `visual_continuity_package.world_lock` is palette / material /
hero **props**. Banned keys (`wardrobe`, `hair`, `face`, `must_show`, …) FAIL
continuity. Appearance lives on `character_variant`.

### 5. Quote before spend; do not blind-retry 402

`lib/metered_provider.py` `quote_metered_tool`. Local H3 `estimate_cost` is 0.
Metered Seedance quotes USD and `requires_confirm` when usd > 0.
`insufficient_credits` / moderation / copyright are **not** retryable.

## Stage map (do not merge the products)

| Factory stage | OM object |
|---|---|
| Script / rewrite | job script + drama compiler |
| Cast extract | `character_ids` + CHARACTER_CARDS |
| Portraits / sheets | bible master sheet + `character_variant.still_refs` |
| Storyboards | `drama_preproduction` / scene_plan |
| Keyframes | SHOT_KEYFRAME 9:16 (not identity plates) |
| Video | local H3 I2VA/FL2VA, or Seedance adapter |
| TTS / compose | existing OM audio/compose tools |

ArcReel's self-hosted MCP is a workstation. Useful as a teacher. Illegal as an
OM merge (AGPL). StarReel MCP is a hosted prepaid client. Do not install it
on this harness.
