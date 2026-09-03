HumanPreference `CONTINUE_SCENE` is now recorded on this job. You are still the production foreman. Cursor will not write the cut list.

Via IPython:

```python
import om_prime_adapter
job = om_prime_adapter.open_job("vid3-blacklisted-chef-90s-v1")
job["next_step"]
om_prime_adapter.get_human_preference("vid3-blacklisted-chef-90s-v1")
```

Then, yourself:

1. Split `scene_b` into ShotContracts / ContentIR on the existing scene proposal (`submit_scene_proposal` with shots now legal).
2. `compile_cut` each non-omitted shot.

Compile law (not a shot list):

- If a cut's intent is locomotion or a real body performance (walk, approach, stop after moving), `motion_obligation=PERFORMANCE`. That compiles to H3 FL2VA. `LIMITED` / `local_compose` / PNG+pan is COMPILE FAIL.
- Two named characters interacting can be `INTERACTION` (preferred `h3_ref2va`). If Ref2VA runtime is missing, compile is `R2VA_RUNTIME_UNAVAILABLE`. Do not FL2VA that cut.
- Intentional hold / reaction / EST may be `NONE` or `LOCAL`. Do not invent extra motion just to use H3.
- Do not generate media in this turn. `compile_cut` writes execution proposals only (`generate=false`).
- Do not polish Scene A. Do not APPROVE. Do not ask Cursor to name the cuts.

If a compile fails, repair that ShotContract and retry compile. If there is no OM `dispatch` action yet, stop after legal compile proposals and report that blocker. Do not fake performance with a still loop.
