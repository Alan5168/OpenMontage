This turn is one cut only: **B2**, once, as a harness acceptance test.

Prove: Prime → OM dispatch → H3 FL2VA → real mp4 → hash-bound Observation → reopen and report.

This is **not** "make B2 look good". Do not continue B3/B4/B5. Do not polish Scene A. Do not APPROVE.

Via IPython:

```python
import om_prime_adapter
job = om_prime_adapter.open_job("vid3-blacklisted-chef-90s-v1")
job["next_step"]
om_prime_adapter.get_human_preference("vid3-blacklisted-chef-90s-v1")
```

Then yourself, once:

```python
om_prime_adapter.dispatch_cut("vid3-blacklisted-chef-90s-v1", "B2", caller="prime")
```

Do not pass `generate=True`. Prime requests execution; OM authorizes and runs H3 FL2VA.

Then `open_job` again. Report only:

- B2 rollout succeeded/failed/blocked technically
- actual observation = ...
- proven_status = ...
- next recommended action = return_to_harness | fix the named runtime blocker

Then **stop**. Do not retry. Do not critique the walk or the kitchen. Do not ask Cursor to run H3 or write receipts.
