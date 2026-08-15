# VID-3 90s job skeleton

Existing pipeline: `anime-hybrid` + profile `fiction_anime_episode`. No new OM pipeline.

`scene_plan.scenes[]` holds shot fields (`animation_class` is a production prior, default LIMITED). A cut cannot spend expensive render until the minimum visual contract passes: locked master sheet + approved source still (`visual_ref.kind=local_image`). Animatic, end frames, and camera choices are not pre-approved. Human identity lock: `python tools/content_studio_gateway.py lock-visuals --i-am-human --master-sheet …`. Do not render VID-3 until that contract passes.
