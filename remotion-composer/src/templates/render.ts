#!/usr/bin/env node
// -------------------------------------------------------------------------
// Template CLI — thin adapter over Remotion.
//
// Usage:
//   npx tsx src/templates/render.ts info --template world-cup-daily --slots slots.json
//   npx tsx src/templates/render.ts resolve --template world-cup-daily --slots slots.json > props.json
//   npx tsx src/templates/render.ts render --template world-cup-daily --slots slots.json --out out/wc-daily.mp4
//
// The `resolve` mode is the cheapest: it prints the JSON that Remotion
// would receive as `--props`, so an agent can inspect or cache it without
// spinning up a render.
// -------------------------------------------------------------------------

import { readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { getTemplate } from "./registry";

type Mode = "info" | "resolve" | "render";

const args = process.argv.slice(2);
const mode = args[0] as Mode;

const flag = (name: string): string | undefined => {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : undefined;
};

const templateId = flag("--template");
const slotsPath = flag("--slots");
const outPath = flag("--out") ?? "out/template.mp4";

if (!mode || !templateId || !slotsPath) {
  console.error(
    "usage: render.ts <info|resolve|render> --template <id> --slots <slots.json> [--out <file.mp4>]",
  );
  process.exit(2);
}

const t = getTemplate(templateId);
const slots = JSON.parse(readFileSync(slotsPath, "utf-8"));
const meta = t.calculateMetadata(slots);

if (mode === "info") {
  console.log(JSON.stringify(
    {
      template: t.id,
      version: t.version,
      description: t.description,
      durationInFrames: meta.durationInFrames,
      durationSeconds: +(meta.durationInFrames / meta.fps).toFixed(2),
      fps: meta.fps,
      width: meta.width,
      height: meta.height,
    },
    null,
    2,
  ));
  process.exit(0);
}

if (mode === "resolve") {
  console.log(JSON.stringify({ template: t.id, slots, meta }, null, 2));
  process.exit(0);
}

if (mode === "render") {
  const compositionId = `template-${t.id}`;
  const tmpProps = `/tmp/template-${t.id}-${Date.now()}.json`;
  require("node:fs").writeFileSync(
    tmpProps,
    JSON.stringify(slots),
  );

  // Remotion needs this template registered in Root.tsx under `compositionId`.
  // If it's not, the agent should register once (see README note below).
  const r = spawnSync(
    "npx",
    [
      "remotion",
      "render",
      "src/index.tsx",
      compositionId,
      outPath,
      "--props",
      tmpProps,
      "--concurrency",
      "50%",
    ],
    { stdio: "inherit" },
  );
  process.exit(r.status ?? 1);
}

console.error(`unknown mode: ${mode}`);
process.exit(2);
