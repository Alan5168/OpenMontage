# MiniMax channel narrator voices

## Current default (OpenMontage)
- **voice_id**: `AlanBilibiliNarrator02`
- model: `speech-2.8-hd`
- source: Logic NT1 5th USB · 短文本.wav + 长文本.wav (2026-07-15 re-record)
- raw peak still ~-28 dBFS → loudnorm applied (less aggressive than v01)

## Versions
| id | notes | listen |
|----|-------|--------|
| AlanBilibiliNarrator01 | first take, quieter source, more room noise after boost | `*_01_demo/activate` if present as AlanBilibiliNarrator01_* |
| AlanBilibiliNarrator02 | second take, default now | `AlanBilibiliNarrator02_demo.mp3` / `_activate.mp3` |

## NT1 5th without interface
Gain lives in System Input volume + RØDE software + mouth distance.
Target peaks **-12 to -6 dBFS** so we can skip loudnorm next time.
