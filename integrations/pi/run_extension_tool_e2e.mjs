#!/usr/bin/env node
/**
 * Invoke content_studio_resume_prime through the TypeScript Pi extension handler.
 * Does NOT call the Python runner directly as the E2E entrypoint.
 */
import { spawn } from "node:child_process";
import { copyFileSync, mkdirSync, readFileSync, writeFileSync, existsSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { parseGatewayStdout } from "./parse_gateway_json.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = process.env.CONTENT_STUDIO_OM_REPO ?? "C:\\ContentStudio\\repos\\OpenMontage";
const EXT_SRC = join(REPO, "integrations", "pi", "content-studio.ts");
const PARSE_SRC = join(REPO, "integrations", "pi", "parse_gateway_json.mjs");
const LIVE_EXT_DIR = join(process.env.USERPROFILE || process.env.HOME || "", ".pi", "agent", "extensions");
const LIVE_EXT = join(LIVE_EXT_DIR, "content-studio.ts");
const LIVE_PARSE = join(LIVE_EXT_DIR, "parse_gateway_json.mjs");
const REPORTS =
  process.env.CONTENT_STUDIO_REPORTS ||
  "C:\\ContentStudio\\reports\\pi-persistent-prime-handoff-continuity-v1";
const PY =
  process.env.CONTENT_STUDIO_PYTHON ||
  "C:\\ContentStudio\\runtime\\OpenMontage-test-venv\\Scripts\\python.exe";
const PI_PKG = join(
  process.env.APPDATA || "",
  "npm",
  "node_modules",
  "@earendil-works",
  "pi-coding-agent",
);
function syncLiveExtension() {
  mkdirSync(LIVE_EXT_DIR, { recursive: true });
  copyFileSync(EXT_SRC, LIVE_EXT);
  copyFileSync(PARSE_SRC, LIVE_PARSE);
}

function execLikePi(command, args, options = {}) {
  return new Promise((resolve) => {
    const env = { ...process.env, ...(options.env || {}) };
    // Pi extension asks for "python"; map to Content Studio venv python.
    const cmd = command === "python" ? PY : command;
    const child = spawn(cmd, args, {
      env,
      cwd: options.cwd || REPO,
      windowsHide: true,
      signal: options.signal,
    });
    let stdout = "";
    let stderr = "";
    const timer = setTimeout(() => {
      child.kill();
    }, options.timeout || 300_000);
    child.stdout.on("data", (d) => {
      stdout += d.toString();
    });
    child.stderr.on("data", (d) => {
      stderr += d.toString();
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      resolve({ stdout, stderr, code: code ?? 1 });
    });
    child.on("error", (err) => {
      clearTimeout(timer);
      resolve({ stdout, stderr: String(err), code: 1 });
    });
  });
}

async function loadExtensionTools(extensionPath) {
  const requireFromPi = createRequire(join(PI_PKG, "package.json"));
  const { createJiti } = requireFromPi("jiti");
  const piAiRoot = join(PI_PKG, "node_modules", "@earendil-works", "pi-ai");
  const piAi = join(piAiRoot, "dist", "index.js");
  const piAiCompat = join(piAiRoot, "dist", "compat.js");
  const piAgent = join(PI_PKG, "dist", "index.js");
  const jiti = createJiti(import.meta.url, {
    interopDefault: true,
    alias: {
      "@earendil-works/pi-ai": piAi,
      "@earendil-works/pi-ai/compat": piAiCompat,
      "@earendil-works/pi-coding-agent": piAgent,
      "@mariozechner/pi-ai": piAi,
      "@mariozechner/pi-ai/compat": piAiCompat,
      "@mariozechner/pi-coding-agent": piAgent,
    },
  });
  const tools = new Map();
  const pi = {
    registerTool(def) {
      tools.set(def.name, def);
    },
    exec: execLikePi,
  };
  const mod = await jiti.import(pathToFileURL(extensionPath).href);
  const factory = mod.default || mod;
  factory(pi);
  return tools;
}

function parseArgs(argv) {
  const out = { projectId: "fixture-pi-resume-e2e", extension: LIVE_EXT };
  for (let i = 2; i < argv.length; i += 1) {
    if (argv[i] === "--project-id") out.projectId = argv[++i];
    else if (argv[i] === "--extension") out.extension = argv[++i];
    else if (argv[i] === "--out") out.out = argv[++i];
  }
  return out;
}

async function main() {
  const args = parseArgs(process.argv);
  syncLiveExtension();
  // Prove the old lastIndexOf path fails on the previous receipt, and new parser passes.
  const samplePath = join(REPORTS, "PI_EXTENSION_E2E_RECEIPT.json");
  let parseRegression = { status: "SKIP" };
  if (existsSync(samplePath)) {
    const raw = readFileSync(samplePath, "utf8");
    let oldFail = false;
    try {
      JSON.parse(raw.slice(raw.lastIndexOf("{")));
    } catch {
      oldFail = true;
    }
    const parsed = parseGatewayStdout(raw);
    parseRegression = {
      status: oldFail && parsed.status === "PASS" ? "PASS" : "FAIL",
      old_lastIndexOf_failed: oldFail,
      new_parser_status: parsed.status,
      new_parser_job_id: parsed?.evidence?.job_id || parsed?.request?.project_id,
    };
  }

  const tools = await loadExtensionTools(args.extension);
  const tool = tools.get("content_studio_resume_prime");
  if (!tool || typeof tool.execute !== "function") {
    throw new Error("content_studio_resume_prime tool not registered by TypeScript extension");
  }

  const started = Date.now();
  const result = await tool.execute("e2e-tool-call", { projectId: args.projectId }, AbortSignal.timeout(300_000));
  const details = result?.details || parseGatewayStdout(result?.content?.[0]?.text || "");
  const payload = {
    status: details.status === "PASS" ? "PASS" : "FAIL",
    entry: "integrations/pi/content-studio.ts content_studio_resume_prime execute()",
    live_extension_path: args.extension,
    synced_from_repo: EXT_SRC,
    project_id: args.projectId,
    evidence_job_id: details?.evidence?.job_id,
    expected_job_id: details?.evidence?.expected_job_id,
    same_project_ok:
      details?.status === "PASS" &&
      details?.evidence?.job_id === args.projectId &&
      details?.evidence?.expected_job_id === args.projectId,
    parse_regression: parseRegression,
    elapsed_seconds: Number(((Date.now() - started) / 1000).toFixed(3)),
    tool_result: details,
    CONTENT_STUDIO_EVIDENCE_JOB_ID_used: false,
    python_runner_direct: false,
  };

  mkdirSync(REPORTS, { recursive: true });
  const outPath = args.out || join(REPORTS, "PI_EXTENSION_TS_TOOL_E2E_RECEIPT.json");
  writeFileSync(outPath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
  console.log(JSON.stringify({ status: payload.status, same_project_ok: payload.same_project_ok, outPath }, null, 2));
  if (payload.status !== "PASS" || !payload.same_project_ok) process.exit(1);
  if (parseRegression.status === "FAIL") process.exit(2);
}

main().catch((err) => {
  console.error(JSON.stringify({ status: "FAIL", error: String(err?.stack || err) }, null, 2));
  process.exit(1);
});
