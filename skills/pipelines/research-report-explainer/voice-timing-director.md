# Research Report Explainer — Voice Timing Director

The approved human recording is the canonical clock. Use ASR or force alignment to create schema-valid `voice_timing` with audio hash, transcript hash, segment/word timings, and `clock_hash`.

Never estimate timings from character count once human audio exists. A changed recording invalidates prior voice timing, scene plan, captions, compose, QA, and final gate by hash.
