# VID-3 90s job skeleton

Existing pipeline: `anime-hybrid` + profile `fiction_anime_episode`. No new OM pipeline.

`scene_plan.scenes[]` holds shot fields (`animation_class`, frame refs, model route, `generation_status`). Pi may drop `submitted/completed/failed` events; only OM writes cut status. Do not render until Alan locks stills, animatic, and the master sheet.
