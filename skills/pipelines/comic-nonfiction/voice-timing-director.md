# Comic Nonfiction — Voice Timing Director

For nonfiction profiles, align Alan's recording with ASR or force alignment and write `voice_timing`. For an explicitly dialogue-estimated fiction adapter, mark `clock_source: DIALOGUE_OR_ESTIMATE` and revalidate against final audio later.

On Windows Mandarin jobs, prefer `sensevoice_transcriber` (official FunASR SenseVoiceSmall weights) and keep `transcriber`/faster-whisper as fallback. The approved script is lexical truth; ASR CTC timestamps are clock truth. Record FunASR model attribution and the model-card license. Keep SenseVoice on fp32 until the pinned runtime's Float/Half VAD path passes a real regression test.

Changing the recording invalidates scene plan, captions, compose, QA, and final gate. Character-count timing is never authoritative after real audio exists.
