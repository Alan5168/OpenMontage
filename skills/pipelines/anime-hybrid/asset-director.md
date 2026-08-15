# Anime Hybrid — Asset, Edit, and Compose Director

Join every generated still, H3 clip, 2.5D hold, and deterministic overlay to the canonical cut id. Record prompt, seed, model, hash, license, continuity inputs, and route. Readable text is never generated into imagery.

Do not call `video_selector`, H3/Comfy, or `video_compose` for a cut that fails the minimum visual contract. `lib/shot_production_gate.py` locks identity (master sheet) and an approved source still on disk. It does not freeze camera, end frames, motion amount, or metaphor. Overlay L0 runs before expensive I2V. A stored `animation_class` is a production prior; missing class drafts as LIMITED.

Edit and compose repair only failed cuts. Final dialogue/audio timing must be revalidated even when scene planning began from an estimate.

At compose, read the approved `render_runtime` from `decision_log`; never infer or silently replace it. Route `render_runtime="remotion"` to Remotion/FFmpeg and `render_runtime="hyperframes"` to HyperFrames. If the selected runtime is unavailable, stop and surface the constraint instead of falling back.
