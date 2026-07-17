---
name: minimax-tts
description: Generate Mandarin/multilingual narration with MiniMax Speech (Token Plan t2a_v2). Use when OpenMontage needs MiniMax TTS, speech-2.8-hd, or mmx speech synthesize.
---

# MiniMax TTS

Requires `MINIMAX_API_KEY` (Token Plan subscription key `sk-cp-...`) in
`~/.codex/skills.env` and/or OpenMontage `.env`.

## Channel primary voice (2026-07-15)

| Setting | Value |
|---------|--------|
| Provider | **minimax** (via `tts_selector` default) |
| Model | `speech-2.8-hd` |
| Voice ID | **`AlanBilibiliNarrator02`** (Alan Bilibili long-form clone) |
| Fallback clone | `AlanBilibiliNarrator01` (noisier first take) |

Do **not** default to system `female-shaonv` for channel production.

## Preferred paths

| Path | When |
|------|------|
| OpenMontage tool `minimax_tts` | Pipeline / selector / automated production |
| CLI `mmx speech synthesize` | One-off agent or shell smoke |
| HTTP `POST /v1/t2a_v2` | Custom scripts |

Do **not** revive the old custom `minimax-multimodal` skill for TTS — official
`mmx` covers speech/image/video/music/search. Install agent skill metadata with:

```bash
npx skills add MiniMax-AI/cli -y -g
```

## CLI

```bash
mmx auth login --api-key "$MINIMAX_API_KEY"
mmx config set --key region --value cn
mmx speech synthesize \
  --text "欢迎使用 MiniMax 语音合成" \
  --voice AlanBilibiliNarrator02 \
  --model speech-2.8-hd \
  --out voiceover.mp3
mmx speech voices   # list system voice IDs (clones are separate)
```

## OpenMontage

```python
from tools.audio.minimax_tts import MiniMaxTTS
# or via selector:
from tools.audio.tts_selector import TTSSelector

# preferred_provider defaults to minimax when available;
# voice defaults to AlanBilibiliNarrator02 (env or DEFAULT_VOICE)
result = TTSSelector().execute({
    "text": "如果 AI 真的会改变未来，普通人到底该怎么参与？",
    "output_path": "artifacts/narration.mp3",
})
# optional explicit:
# "voice_id": "AlanBilibiliNarrator02",
```

Writing / script work (agent-side LLM, not a runtime TTS call) should use
LiteLLM alias **`MiniMax-M3-creative`** per `config.yaml` (`llm.model`).
Mechanical short tasks may use `m3` / `MiniMax-M3`.

Env defaults:

```text
MINIMAX_API_HOST=https://api.minimaxi.com
MINIMAX_TTS_MODEL=speech-2.8-hd
MINIMAX_TTS_VOICE=AlanBilibiliNarrator02
```

Artifacts / demos: `artifacts/voice_clone/AlanBilibiliNarrator02_*.mp3`

## Notes

- Sync API cap ~10k characters; longer scripts → split or use async t2a docs.
- Token Plan quota is shared with M3 chat / video / music — watch `mmx quota`.
- Domestic host is `api.minimaxi.com` (region `cn`); global is `api.minimax.io`.
- Clone must be used in TTS within 7 days of creation (already activated).
