# Research Report Explainer — Seven-Column Scene Director

Create the canonical `scene_plan`; each `scenes[].id` is the downstream cut key. Run the strict seven-column validator before checkpointing. Every row exposes: scene group, cut id, visual/layout reference, action/camera content plus exact layout prompt, dialogue/VO, clock-bound duration, and sound intent.

Use `image_selector` only for static layout references. One new layout gets one take; reuse cuts point to the source cut; hero cuts may receive one extra take. A readable placeholder is allowed after three same-root provider failures but cannot become a final asset. Stop at the Sceneplan Gate.
