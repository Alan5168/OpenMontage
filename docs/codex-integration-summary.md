# Codex Integration for OpenMontage — Implementation Summary

**Date:** 2026-09-01
**Status:** Step 1 (TUI entry) ✅ | Step 2 (Tool bridge) ✅ | Step 3 (Skill + config) ✅

## What Was Done

### Step 1: `codex-content.cmd` — Interactive TUI Entry

**File:** `C:\ContentStudio\bin\codex-content.cmd`

- Same environment variables as `content.cmd` (CONTENT_STUDIO_ROOT, OM repo, projects dir)
- Same proxy sanitization logic
- Launches `codex` TUI instead of Pi
- Read-only companion — no OM Gate/dispatch authority

**Usage:**
```powershell
C:\ContentStudio\bin\codex-content.cmd
```

### Step 2: Tool Bridge — `codex_exec` + `codex_tui` BaseTools

**Files:**
- `tools/development/__init__.py`
- `tools/development/codex_bridge.py` — `CodexExec` + `CodexTui` tool classes
- `tools/development/codex_mcp_bridge.py` — MCP server wrapper (experimental)

**`CodexExec`** wraps `codex exec` as a standard OM BaseTool:
- `capability="development"`, `provider="codex"`, `runtime="LOCAL"`
- Parameters: `prompt`, `cwd`, `model`, `sandbox`, `output_path`, `output_schema`, `approve_for_me`, `operation`
- Auto-locates codex binary (npm global or PATH)
- UTF-8 encoding with error replacement for Windows compatibility

**`CodexTui`** launches interactive TUI (non-blocking Popen)

**`codex_mcp_bridge.py`** provides an MCP-over-stdio server for clients that support MCP.
- Falls back to raw JSON-RPC if MCP SDK not installed
- Exposes `codex_exec` and `codex_review` tools

### Step 3: Pi Skill — Teaching Pi to Use Codex

**File:** `~/.pi/agent/skills/codex-cli/SKILL.md`

Pi does NOT support MCP natively (per README: "No MCP. Build CLI tools with READMEs").
The skill teaches Pi:
- When to delegate to Codex (debug workflows, write skills, run tests)
- When NOT to (creative direction, production decisions)
- Exact command syntax for `codex exec`, `codex` TUI, `codex review`
- File path conventions within OM workspace
- Sandbox mode selection
- Installation instructions if codex not found

## Key Findings

| Fact | Impact |
|------|--------|
| `codex app-server daemon` is Unix-only | Cannot use full app-server protocol on Windows |
| `codex mcp-server` is deprecated | Not recommended for new integrations |
| Pi does NOT support MCP | Must use Skills (Markdown) to teach Pi |
| `codex exec` works perfectly | Primary bridge mechanism |
| `codex` TUI works perfectly | Interactive entry point |
| Codex Desktop app already installed | `OpenAI.Codex_26.825.6671.0` |
| `~/.codex/config.toml` has OV MCP | Codex already connects to OpenViking |

## Architecture (Windows Reality)

```
┌─────────────────────────────────────────────────────────────┐
│  Frontends (read-only companions, no production write)       │
│  [Pi] [Codex TUI] [Antigravity] [QoderWork] [Hermes] ...    │
└──────────────┬──────────────────────────────────┬───────────┘
               │                                  │
               │  Pi Skill teaches Pi             │  codex-content.cmd
               │  to call `codex exec`            │  launches TUI
               │                                  │
               ▼                                  ▼
┌──────────────────────────┐      ┌──────────────────────────┐
│  Pi calls codex exec     │      │  Codex TUI (interactive) │
│  via bash tool           │      │  User types directly     │
└──────────┬───────────────┘      └──────────┬───────────────┘
           │                                 │
           └────────────┬────────────────────┘
                        ▼
           ┌────────────────────────┐
           │  codex exec / codex    │
           │  (OpenAI Codex 0.152)  │
           └────────────┬───────────┘
                        │
           ┌────────────┴───────────┐
           │                        │
           ▼                        ▼
   ┌───────────────┐      ┌──────────────────┐
   │  Read files   │      │  Modify files    │
   │  Run tests    │      │  (workspace-write)│
   │  Check state  │      │                  │
   └───────┬───────┘      └────────┬─────────┘
           │                       │
           ▼                       ▼
   ┌──────────────────────────────────────┐
   │  OpenMontage Workspace               │
   │  tools/ skills/ pipeline_defs/ lib/  │
   └──────────────────────────────────────┘
```

## What Codex CAN Do (after this integration)

1. **Debug ComfyUI workflows** — Read/modify `tools/_comfyui/workflows/*.json`, run generation tests
2. **Write/modify skills** — Edit `skills/pipelines/<pipeline>/*.md`, `.agents/skills/**/*.md`
3. **Write/modify pipelines** — Edit `pipeline_defs/*.yaml`, run validation
4. **Run tests** — `python -m pytest`, `python -c "..."` for state inspection
5. **Refactor code** — Any Python/JSON/YAML in the OM workspace
6. **Check OM status** — Read checkpoints, query tool registry, inspect artifacts

## What Codex CANNOT Do (by design)

- ❌ Approve OM Gates (SCENEPLAN, CONTENT, FINAL) — human only
- ❌ Dispatch Prime — Pi/Prime only
- ❌ Modify checkpoints directly — OM Gate protocol
- ❌ Access Pi's conversation context — stateless per invocation
- ❌ Use app-server daemon — Unix-only, not available on Windows

## Verification Results

```
CodexExec tool:     status=available, binary found
CodexTui tool:      status=available
codex --version:    codex-cli 0.152.0
codex exec "...":   Successfully read AGENT_GUIDE.md, provided architecture summary
Pi skill:           Written to ~/.pi/agent/skills/codex-cli/SKILL.md
codex-content.cmd:  Created at C:\ContentStudio\bin\codex-content.cmd
```

## Next Steps (Optional)

1. **Test with real tasks** — Ask Pi to "use codex to debug the wan22 workflow"
2. **Add more Codex tools** — e.g., `codex_review` for automated code review in CI
3. **Build a web UI** — If desired, use `codex_mcp_bridge.py` as backend for a simple web interface
4. **Monitor quota** — Track Codex subscription usage across sessions
