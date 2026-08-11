# Research Report Explainer — Edit and Compose Director

Keep edit cut ids identical to `scene_plan.scenes[].id`. Subtitle and visual timings follow `voice_timing`; changing pictures never shifts the approved audio clock. Remotion/FFmpeg owns readable text, safe areas, subtitles, mix, and export.

Compose records all input hashes and the final hash. A source, voice, scene-plan, asset, or edit hash change invalidates later PASS artifacts automatically; never reuse a stale final review.
