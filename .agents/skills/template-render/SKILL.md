---
name: template-render
description: Render daily/batch short-form videos using the template slot-filling layer. Use when routing daily video production, batch template renders, or slot-based video generation through Remotion templates. Covers the template CLI (info/resolve/render), slot schemas, registry, and composition metadata calculation.
---

# Template Render

Slot-based template system for producing parameterized short-form videos (9:16 vertical, ~55s, Douyin/XiaohongShu pacing) via Remotion. Templates define slot schemas; the CLI resolves slots to composition props and invokes Remotion.

## When to Use

- Daily/batch video production from structured data (match results, standings, news stories)
- Rendering a registered template with slot JSON
- Inspecting template metadata or resolved props before rendering
- Adding new templates to the registry

## Architecture

```
slots.json  ──→  render.ts (CLI)  ──→  registry.ts  ──→  Remotion render
                      │
                      ├─ info:     print template metadata + duration
                      ├─ resolve:  print resolved props JSON
                      └─ render:   invoke remotion render with --props
```

**Working directory:** All commands run from `remotion-composer/`, not the repo root.

## File Map

| File | Role |
|------|------|
| `src/templates/render.ts` | CLI adapter: `info`, `resolve`, `render` modes |
| `src/templates/registry.ts` | Template registry, `getTemplate(id)` lookup |
| `src/templates/slots.types.ts` | Slot type definitions (MatchSlot, StandingRowSlot, etc.) |
| `src/templates/world-cup-daily.tsx` | Composition component + `calculateWorldCupDailyMetadata` |
| `src/templates/world-cup-daily.d12.json` | Sample slots for Day 12 |

## CLI Commands

### info — Template metadata

```bash
npx tsx src/templates/render.ts info --template world-cup-daily --slots slots.json
```

Prints template ID, version, description, duration (frames + seconds), fps, dimensions. No Remotion invocation.

### resolve — Resolved props

```bash
npx tsx src/templates/render.ts resolve --template world-cup-daily --slots slots.json
```

Prints the full `{ template, slots, meta }` JSON that Remotion would receive as `--props`. Useful for debugging or caching.

### render — Full render

```bash
npx tsx src/templates/render.ts render --template world-cup-daily --slots slots.json --out out/wc-daily.mp4
```

Invokes `remotion render` with the resolved props. Default output: `out/template.mp4`.

## Slot Schema

### WorldCupDailySlots

```typescript
{
  edition: string;              // "Day 12 · June 22, 2026"
  host: {
    name: string;
    avatar?: AssetSlot;
    voice?: string;             // TTS voice id
  };
  intro: {
    title: string;              // "今日世界杯"
    subtitle?: string;
    theme?: string;             // key from Root.tsx THEMES
  };
  stories: StorySlot[];         // news cards
  matches: MatchSlot[];         // match result cards
  standings?: {
    group: string;              // "Group A"
    rows: StandingRowSlot[];
  };
  outro?: {
    cta?: string;
    endCardAsset?: AssetSlot;
  };
  narration?: {
    audioSrc: string;           // filename in public/ (not full path)
    captions?: { text: string; startMs: number; endMs: number }[];
  };
}
```

### Slot Primitives

| Type | Purpose |
|------|---------|
| `AssetSlot` | Media reference: video/image/audio + src + duration |
| `MatchSlot` | Match result: teams, scores, kickoff, stage, venue |
| `StandingRowSlot` | Group table row: team, played, won, drawn, lost, points |
| `StorySlot` | News card: headline, body, source, optional asset |

## Metadata Calculation

Each template exports a `calculateMetadata(slots)` function that returns:

```typescript
{
  durationInFrames: number;
  fps: number;              // typically 30
  width: number;            // 1080 for 9:16
  height: number;           // 1920 for 9:16
}
```

Duration is computed from slot content (number of stories, matches, narration length). The CLI uses this to validate before rendering.

## Adding a New Template

1. **Define slots** in `slots.types.ts`:
   ```typescript
   export interface MyTemplateSlots {
     // slot fields
   }
   ```

2. **Create composition** in `src/templates/my-template.tsx`:
   - Export default component: `React.FC<MyTemplateSlots>`
   - Export `calculateMyTemplateMetadata(slots: MyTemplateSlots)`

3. **Register** in `registry.ts`:
   ```typescript
   import { MyTemplate, calculateMyTemplateMetadata } from "./my-template";
   import type { MyTemplateSlots } from "./slots.types";

   export const TEMPLATES = {
     // existing templates
     "my-template": {
       id: "my-template",
       version: "1.0.0",
       description: "...",
       composition: MyTemplate,
       calculateMetadata: calculateMyTemplateMetadata,
     } as TemplateManifest<MyTemplateSlots>,
   };
   ```

4. **Register composition** in `Root.tsx` with id `template-my-template` (no underscores).

## Known Pitfalls

### Composition ID regex

Remotion composition IDs must match `[a-zA-Z0-9\u4e00-\u9fa5-]+`. **Underscores are rejected.** Use `template-{id}` format, not `__template__{id}`.

### Sequence duration guards

When `defaultProps` in `Root.tsx` has empty arrays, `<Sequence durationInFrames={...}>` can evaluate to 0, which Remotion rejects. Guard with:

```tsx
{slots.stories.length > 0 && (
  <Sequence from={...} durationInFrames={...}>
    <Stories />
  </Sequence>
)}
```

### Audio file paths

`<Audio src>` resolves via `staticFile()`, which looks in `public/`. Use bare filenames, not paths:

```tsx
// ✓ Correct
<Audio src="wc-d12-narration.mp3" />

// ✗ Wrong
<Audio src="out/wc-d12-narration.mp3" />
```

### Silent audio generation

When generating placeholder audio for testing:

```bash
# ✓ Correct — explicit channel layout
ffmpeg -f lavfi -i "anullsrc=r=22050:cl=mono" -t 60 -c:a libmp3lame -q:a 9 public/placeholder.mp3

# ✗ Wrong — missing cl= parameter
ffmpeg -f lavfi -i "anullsrc=r=22050:mono" -t 60 placeholder.mp3
```

### defaultProps must render cleanly

Remotion renders with `defaultProps` before applying `--props`. Ensure `defaultProps` in `Root.tsx` produces a valid (if empty) render. Test with:

```bash
npx remotion preview src/index.tsx
```

## Example Workflow

```bash
# 1. Prepare slots
cat > slots.json <<EOF
{
  "edition": "Day 15 · June 25, 2026",
  "host": { "name": "AI Host" },
  "intro": { "title": "今日世界杯" },
  "stories": [
    { "headline": "Argentina advances on penalties" },
    { "headline": "Mbappé hat-trick stuns Denmark" }
  ],
  "matches": [
    {
      "kickoff": "21:00",
      "teamA": "Argentina",
      "teamB": "Australia",
      "scoreA": 2,
      "scoreB": 1,
      "stage": "R16",
      "status": "final"
    }
  ],
  "narration": {
    "audioSrc": "wc-d15-narration.mp3"
  }
}
EOF

# 2. Check metadata
npx tsx src/templates/render.ts info --template world-cup-daily --slots slots.json

# 3. Resolve props (optional, for debugging)
npx tsx src/templates/render.ts resolve --template world-cup-daily --slots slots.json | jq .meta

# 4. Render
npx tsx src/templates/render.ts render --template world-cup-daily --slots slots.json --out out/wc-d15.mp4
```

## Render Verification

After rendering, verify output:

```bash
ffprobe -v error -show_entries stream=codec_name,width,height,nb_frames,duration \
  -of default=noprint_wrappers=1 out/wc-daily.mp4
```

Expected: H.264 1080×1920, ~59s, ~1770 frames @ 30fps, AAC audio.

## Never Do

- Use underscores in composition IDs
- Skip length guards on Sequences that depend on slot arrays
- Reference audio files with paths outside `public/`
- Omit `calculateMetadata` export — the CLI requires it
- Hardcode fps/dimensions in composition — use metadata calculation
