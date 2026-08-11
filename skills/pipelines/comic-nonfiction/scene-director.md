# Comic Nonfiction — Seven-Column Scene Director

The canonical `scene_plan.scenes[].id` is every cut's join key. Validate all seven human-facing columns and the voice-clock join. Generate one textless API layout reference per new layout; reuse cuts point to the originating cut.

Each reference records prompt, negative prompt, provider, model, seed, size, request id, plan/cost usage, output hash, and license policy. H3 is forbidden before the Sceneplan Gate is approved.

The human Sceneplan Gate must keep three diagnostic layers visibly separate for every cut:

1. **Visual intent / action** — the effect the director wants, independent of any model syntax.
2. **Exact image API request prompt** — the positive prompt sent by OpenMontage, with negative prompt and provider-side prompt-extension settings disclosed. Reuse cuts say that no image API was called and name the source cut.
3. **Generated or reused result** — the selected reference/provenance or reuse source that the reviewer can compare against the intent and request.

Review decisions distinguish `change intent`, `change prompt`, and `regenerate`; do not collapse these into a generic `change` because they assign failure to different stages.
