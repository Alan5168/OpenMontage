# Creative Loop Director (v0.1)

This stage is graph-enforced. `render_success=true` is not SEE.

## SEE

Run `python tools/creative_loop.py extract-frames --mp4 <draft.mp4> --out <dir> --anchors <script times>`.
Required frames: t=0, every ~4 seconds, and script anchors. Machine checks (duration, black frame, hash, probe) run first and can block. The model cannot override a machine FAIL.

## Intent

Frozen contract fields are only `intent`, `must_convey`, and `creative_freedom`.
Do not expand this into hook / camera / transition / emotion / color rules. Intent describes the goal, not the solution.

## Critique

Every finding must cite `t_start`, `t_end`, `frame_ids`, and explain why the rendered artifact fails the frozen intent.
Reject generic notes such as "节奏可以更紧凑" or "视觉可以更丰富".
A valid finding names the seconds, the frame, and the missing causal link.

## Repair

Write a segment-scoped `repair_plan`, patch only those seconds, then `rerender` (reentry of `compose`). The new mp4 hash must differ. Re-run machine gates on the new hash. Old QA is invalid.

## Experience

Write `LEARNING_EVENT` with `constraint_class`, `applies_when`, `counterexample`, and `auto_retrieve: false`.
Do not retrieve the event into the next film in v0.1. Human accept/reject is a separate gate. Model judge cannot PASS the loop.
