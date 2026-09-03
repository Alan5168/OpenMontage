B2 dispatch is blocked. You are still the production foreman. This is not an H3 failure and not a cue to retry.

Via IPython:

```python
import om_prime_adapter
job = om_prime_adapter.open_job("vid3-blacklisted-chef-90s-v1")
job["next_step"]
job["production_world"]["prerequisite"]
job["production_world"]["character_identities"]
```

Root prerequisite is **Lucien identity lock**, then a B1 NONE keyframe, then that keyframe as B2.start_frame_ref.

Do this yourself:

1. `om_prime_adapter.submit_prerequisite_plan("vid3-blacklisted-chef-90s-v1", caller="prime")`
2. `om_prime_adapter.propose_identity_candidates("vid3-blacklisted-chef-90s-v1", caller="prime")`

Then stop and wait. Do not lock identity. Alan must see plates A and B before choosing.

Identity candidates are **character plates** (bust-up, grey studio, face/hair/scars/base wardrobe). They are not B1 kitchen shots.

Alan: `A` / `B` / `NEITHER` on `identity:lucien_mercer` only after looking at the two plates.

B1 keyframe is not a Human gate. After Lucien is locked, a later turn `produce_keyframe(B1)` makes a canonical start-state still, OM-validated, then binds `B2.start_frame_ref = B1.final`. That is not APPROVED.

Do not:
- retry `dispatch_cut(B2)`
- write `start_frames/B2.png`
- generate a random Lucien to unstick H3
- send B1 to H3 (B1 is NONE)
- lock identity yourself
- polish Scene A
- APPROVE

If candidate generation fails, report that honestly and stop. After Alan locks Lucien, a later turn may `produce_keyframe(..., "B1")` and bind it as B2.start_frame_ref. Not this turn unless identity is already locked.
