#!/usr/bin/env node
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const extensionPath = process.argv[2] || join(here, "content-cockpit.ts");
const openVikingPath = join(dirname(extensionPath), "openviking.ts");
const piPackage = join(
  process.env.APPDATA || "",
  "npm",
  "node_modules",
  "@earendil-works",
  "pi-coding-agent",
);
const requireFromPi = createRequire(join(piPackage, "package.json"));
const { createJiti } = requireFromPi("jiti");
const piAiRoot = join(piPackage, "node_modules", "@earendil-works", "pi-ai");
const jiti = createJiti(import.meta.url, {
  interopDefault: true,
  alias: {
    "@earendil-works/pi-ai": join(piAiRoot, "dist", "index.js"),
    "@earendil-works/pi-coding-agent": join(piPackage, "dist", "index.js"),
  },
});

const mod = await jiti.import(pathToFileURL(extensionPath).href);
const openVikingMod = await jiti.import(pathToFileURL(openVikingPath).href);
const index = {
  revision: 9,
  focus_job_id: "old-completed-job",
  active_handoffs: {
    "old-completed-job": {
      job_id: "old-completed-job",
      status: "COMPLETED",
      summary: "old",
    },
    "current-job": {
      job_id: "current-job",
      task: "Current work",
      status: "ACTIVE",
      summary: "Current summary",
      pending_gate: "A_REVIEW",
      next_action: "Review the sample",
      decisions_made: ["Use the approved voice"],
      pointers: ["C:\\ContentStudio\\jobs\\current-job\\working\\sample.mp3"],
      source_writeback: "C:\\ContentStudio\\jobs\\current-job\\working\\SESSION_WRITEBACK_20260903.md",
      updated_at: "2026-09-03T20:00:00+08:00",
    },
  },
};

assert.equal(mod.selectHotHandoff(index, "current-job")?.jobId, "current-job");
assert.equal(mod.selectHotHandoff(index, "missing-job"), null);
assert.equal(mod.selectHotHandoff(index, null)?.jobId, "old-completed-job");
assert.match(mod.formatHotHandoff(index, "current-job"), /Current summary/);
assert.match(mod.formatHotHandoff(index, "current-job"), /Use the approved voice/);
assert.match(mod.formatHotHandoff(index, "missing-job"), /Do not substitute a different focus job/);
assert.equal(mod.shouldAutoRecall("昨天已经做过 TTS 了"), true);
assert.equal(mod.shouldAutoRecall("现在状态是什么"), false);
assert.doesNotMatch(mod.redactMemorySecrets("key sk-abcdefghijklmnop"), /sk-abcdefghijklmnop/);

const recall = mod.formatRecallResults({
  result: {
    memories: [
      { uri: "viking://user/alan/peers/pi/memories/entities/voice.md", score: 0.8, abstract: "Alan voice" },
      { uri: "viking://user/alan/memories/events/.overview.md", score: 0.9, abstract: "overview" },
      { uri: "viking://user/alan/peers/pi/memories/patterns/low.md", score: 0.1, abstract: "low" },
    ],
  },
});
assert.match(recall, /Alan voice/);
assert.doesNotMatch(recall, /overview|low/);

const tools = new Map();
const commands = new Map();
const events = new Map();
mod.default({
  registerTool(def) {
    tools.set(def.name, def);
  },
  registerCommand(name, def) {
    commands.set(name, def);
  },
  on(name, handler) {
    events.set(name, handler);
  },
  sendMessage() {},
  async exec(command, args) {
    if (String(command).toLowerCase().includes("nvidia-smi")) {
      return { code: 1, stdout: "", stderr: "not needed in memory smoke test" };
    }
    if (Array.isArray(args) && args.at(-1) === "state") {
      return {
        code: 0,
        stdout: JSON.stringify({
          job: "vid-the-moment-s01e01-zh-v1",
          status: "SCRIPT_READY_TTS_PROMPT_REVIEW",
          action: "review",
          summary: "EP1 memory smoke state",
          prime_running: false,
          gate_open: false,
        }),
        stderr: "",
      };
    }
    return { code: 0, stdout: "{}", stderr: "" };
  },
});
assert.ok(tools.has("content_studio_hot_handoff"));
assert.ok(commands.has("memory"));
assert.ok(events.has("session_start"));
assert.ok(events.has("before_agent_start"));

const uiState = { statuses: [], widgets: [] };
const ctx = {
  ui: {
    setStatus(name, value) {
      uiState.statuses.push([name, value]);
    },
    setWidget(name, value) {
      uiState.widgets.push([name, value]);
    },
    notify() {},
  },
};
await events.get("session_start")({ reason: "startup" }, ctx);
const injected = await events.get("before_agent_start")({
  prompt: "昨天 EP1 使用的 voice_id 和音色是什么？",
  systemPrompt: "BASE_PROMPT",
});
assert.match(injected.systemPrompt, /Content Studio memory protocol/);
assert.match(injected.systemPrompt, /selected job: vid-the-moment-s01e01-zh-v1/);
assert.match(injected.systemPrompt, /OpenViking automatic recall/);
assert.match(injected.systemPrompt, /qwen-audio-3\.0-tts-plus-alan-0608bece080b4814893df5796b16f341/);
assert.ok(uiState.statuses.length > 0);
assert.ok(uiState.widgets.some(([, value]) => /memory: hot r\d+/.test(String(value))));

const openVikingTools = new Map();
openVikingMod.default({
  registerTool(def) {
    openVikingTools.set(def.name, def);
  },
});
const remember = openVikingTools.get("openviking_remember");
assert.ok(remember);
assert.match(remember.promptGuidelines.join("\n"), /content_studio_hot_handoff/);

console.log(JSON.stringify({
  status: "PASS",
  extensionPath,
  tested: [
    "current-job hot selection beats stale focus",
    "no wrong-job fallback",
    "bounded hot formatting",
    "memory-trigger detection",
    "secret redaction",
    "recall filtering",
    "extension registrations",
    "session-start current-job hot injection",
    "live OpenViking automatic recall injection",
    "task-handoff write-path guidance",
  ],
}, null, 2));
