# Comic Nonfiction — Edit and Compose Director

Edit decisions reuse scene ids and preserve the voice clock. Captions, readable text, safe areas, loudness, and export are deterministic layers. A failed cut is repaired locally without re-rendering accepted cuts.

Compose records input hashes, output probe, cost, GPU wall time, and disk peak. Any upstream hash change invalidates the render and all final PASS artifacts.
