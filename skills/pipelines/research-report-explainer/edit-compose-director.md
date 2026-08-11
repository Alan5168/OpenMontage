# Research Report Explainer — Edit and Compose Director

Keep edit cut ids identical to `scene_plan.scenes[].id`. Subtitle and visual timings follow `voice_timing`; changing pictures never shifts the approved audio clock. Remotion/FFmpeg owns readable text, safe areas, subtitles, mix, and export.

Compose records all input hashes and the final hash. A source, voice, scene-plan, asset, or edit hash change invalidates later PASS artifacts automatically; never reuse a stale final review.

Read the approved `render_runtime` from `decision_log`. Route `render_runtime="remotion"` through Remotion/FFmpeg and `render_runtime="hyperframes"` through HyperFrames; never silently substitute one runtime for the other. If the selected runtime is unavailable, surface the blocker and wait for a recorded change.
