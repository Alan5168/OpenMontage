# Comic Nonfiction — Voice Timing Director

For nonfiction profiles, align Alan's recording with ASR or force alignment and write `voice_timing`. For an explicitly dialogue-estimated fiction adapter, mark `clock_source: DIALOGUE_OR_ESTIMATE` and revalidate against final audio later.

On Windows Mandarin jobs, follow the frozen profile's validated ASR ranking rather than a provider default. Use `sensevoice_transcriber` with the official FunASR SenseVoiceSmall weights as the primary clock, and use `transcriber` with `large-v3-turbo` as the precision backup. The approved script is lexical truth; ASR timestamps are clock evidence, not permission to rewrite approved copy. Record model attribution, runtime, compute type, and fixture evidence.

The current Windows fixture selects SenseVoiceSmall CUDA fp32 for the primary clock. Its pinned FunASR 1.4.1 Float/Half VAD path failed a real regression test, so fp16 remains blocked. The same approved 52.82-second voice selects faster-whisper `large-v3-turbo` CPU int8 for backup: int8 and float32 tied at 0.014851 CER, while int8 used about 1.99 GB peak process RSS and 14.47 seconds versus about 6.86 GB and 28.23 seconds for float32. A model, runtime, device, or compute-type change requires fixture revalidation.

Changing the recording invalidates scene plan, captions, compose, QA, and final gate. Character-count timing is never authoritative after real audio exists.
