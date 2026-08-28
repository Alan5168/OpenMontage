# Windows H3 Capability Plane

This capability plane belongs to the Windows Content Studio. It does not run
MiniMax H3 on macOS and it does not replace OpenMontage's existing video tool.

## Boundary

- `h3.fl2va.base_nvfp4` is the verified default for an approved `I2V_HARD` cut.
- `h3.fl2va.turbo_v4_600` remains an explicit A/B candidate.
- `h3.ref2va.nvfp4` remains an isolated 8190 candidate until a 16 GB runtime
  smoke passes.
- `h3.ref2va.multishot_previs` is previs-only. The pinned upstream JSON is a
  ComfyUI UI workflow, not an API prompt, so OM refuses automatic dispatch
  until an API export is pinned and tested.
- References must be owned, licensed, or generated-owned. Goodcase assets with
  `reference_only_not_for_render` are rejected mechanically.
- Nothing in this package can approve a cut or promote a generated asset.

## Inspect

```powershell
cd C:\ContentStudio\worktrees\h3-capabilities-v1
python tools\h3_capability.py list
python tools\h3_capability.py doctor h3.fl2va.base_nvfp4 `
  --model-root C:\models\h3-nvfp4
```

Use `--verify-hashes` for a release gate, not every health poll; hashing the
full stack reads more than 32 GiB.

## Install the pinned Ref2VA and multishot assets

Download only to staging:

```powershell
hf download FenomAI/MiniMax-H3 `
  minimax_h3_ref2va_pruned_nvfp4.safetensors `
  --revision 15646562c19be9d62aee6d28a7070d00d026027c `
  --local-dir C:\models\h3-nvfp4\staging\ref2va
```

Then verify and promote atomically:

```powershell
python tools\install_h3_ref2va_assets.py `
  --staging-file C:\models\h3-nvfp4\staging\ref2va\minimax_h3_ref2va_pruned_nvfp4.safetensors `
  --model-root C:\models\h3-nvfp4 `
  --runtime-root C:\ContentStudio\runtime
```

The installer preserves the exact upstream workflow under
`runtime\h3\raw\`, creates an NVFP4-adapted UI copy, and writes an install
receipt. `ASSETS_INSTALLED_NOT_RUNTIME_PROVEN` is not a runtime PASS.

## Compile a legal baseline dispatch

The compiler consumes a route receipt after the existing motion and production
gates have passed:

```powershell
python tools\h3_capability.py compile `
  --cut-id c001 `
  --rights owned
```

Candidate capabilities require their explicit ID. Ref2VA additionally requires
`--adapter-gate-pass`. Multishot still fails closed because its upstream file is
not an API-format workflow.

## Runtime gate

Use only the clean canary on port 8190. Do not modify legacy `C:\ComfyUI` and do
not infer production readiness from a successful download. A future runtime
gate must record server/node health, model hashes, peak VRAM, wall time, and a
playable output before changing `h3.ref2va.nvfp4` out of candidate status.

MiniMax H3 weights and derived workflows remain subject to the MiniMax H3
Community License. Public/commercial use needs the separate license review and
AI-generated disclosure required by that license.
