# Comic Nonfiction — Voice Timing Director

For nonfiction profiles, align Alan's recording with ASR or force alignment and write `voice_timing`. For an explicitly dialogue-estimated fiction adapter, mark `clock_source: DIALOGUE_OR_ESTIMATE` and revalidate against final audio later.

Changing the recording invalidates scene plan, captions, compose, QA, and final gate. Character-count timing is never authoritative after real audio exists.
