# License boundary (Windows Content Studio)

OpenViking 0.4.13 is AGPLv3. It stays an independent process:

- Install: `C:\ContentStudio\runtime\openviking-0.4.13\`
- Config: `C:\ContentStudio\config\openviking\ov.conf`
- Access: public CLI (`ov.exe`) and loopback HTTP `127.0.0.1:1933` only
- OpenMontage talks to it through `tools/om_context_bridge.py`; it does not vendor, fork, or copy OpenViking source into this repo

Qdrant, Qwen3-Embedding, H3, ComfyUI, ASR, and Remotion remain separate runtimes. Running OpenViking locally does not grant a right to ship AGPL code inside a closed OpenMontage subscription; that needs a later license review.
