# Comic Nonfiction — Edit and Compose Director

Edit decisions reuse scene ids and preserve the voice clock. Captions, readable text, safe areas, loudness, and export are deterministic layers. A failed cut is repaired locally without re-rendering accepted cuts.

Compose records input hashes, output probe, cost, GPU wall time, and disk peak. Any upstream hash change invalidates the render and all final PASS artifacts.

Read the approved `render_runtime` from `decision_log`. Route `render_runtime="remotion"` through Remotion/FFmpeg and `render_runtime="hyperframes"` through HyperFrames; never silently substitute one runtime for the other. A missing or unavailable approved runtime is a blocker, not permission to default.
