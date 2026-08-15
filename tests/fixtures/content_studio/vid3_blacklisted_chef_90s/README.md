# VID-3 90s job skeleton

Existing pipeline: `anime-hybrid` + profile `fiction_anime_episode`. No new OM pipeline.

`scene_plan.scenes[]` holds shot fields (`animation_class` is intent only). A cut cannot leave planning until `lib/shot_production_gate.py` says `production_ready`: master sheet + animatic files, approved stills on disk, `visual_ref.kind=local_image`. Pi may drop `submitted/completed/failed` events; only OM writes cut status. Human lock: `python tools/content_studio_gateway.py lock-visuals --i-am-human --master-sheet … --animatic …`. Do not render VID-3 until that gate passes.
