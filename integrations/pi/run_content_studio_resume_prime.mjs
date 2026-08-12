#!/usr/bin/env node
/**
 * Canonical body of content_studio_resume_prime.
 * Used by the Pi extension and by the Windows E2E harness.
 */
import { spawn } from "node:child_process";
import { createHash, randomBytes } from "node:crypto";
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parseGatewayStdout } from "./parse_gateway_json.mjs";

const REPO = process.env.CONTENT_STUDIO_OM_REPO ?? "C:\\ContentStudio\\repos\\OpenMontage";
const GATEWAY = join(REPO, "tools", "content_studio_gateway.py");
const PRIME_CLI_JS =
  process.env.PRIME_AGENT_CLI_JS ??
  join(process.env.APPDATA || "", "npm", "node_modules", "prime-agent", "dist", "bundle", "cli.js");
const DEFAULT_KERNEL =
  process.env.CONTENT_STUDIO_PRIME_KERNEL_PYTHON ??
  "C:\\ContentStudio\\runtime\\Prime-kernel-venv\\Scripts\\python.exe";
const PY = process.env.CONTENT_STUDIO_PYTHON ?? "python";

function run(cmd, args, opts = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, {
      env: opts.env || process.env,
      cwd: opts.cwd,
      windowsHide: true,
    });
    let stdout = "";
    let stderr = "";
    const timer = setTimeout(() => {
      child.kill();
      reject(new Error(`timeout running ${cmd} after ${opts.timeout || 300_000}ms`));
    }, opts.timeout || 600_000);
    child.stdout.on("data", (d) => {
      stdout += d.toString();
    });
    child.stderr.on("data", (d) => {
      stderr += d.toString();
    });
    child.on("error", (err) => {
      clearTimeout(timer);
      reject(err);
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      resolve({ code: code ?? 1, stdout, stderr });
    });
  });
}

function parseJsonLine(text) {
  return parseGatewayStdout(text);
}

async function gateway(command, projectId, extra = []) {
  const args = ["-X", "utf8", GATEWAY];
  if (projectId) args.push("--project-id", projectId);
  args.push(command, ...extra);
  const result = await run(PY, args, { timeout: 120_000 });
  const payload = parseJsonLine(result.stdout || result.stderr);
  if (result.code !== 0 || payload.status === "ERROR") {
    throw new Error(payload.error || result.stderr || "gateway failed");
  }
  return payload;
}

function countLines(path) {
  if (!existsSync(path)) return 0;
  const text = readFileSync(path, "utf8");
  if (!text) return 0;
  return text.split(/\r?\n/).filter((l, i, arr) => !(i === arr.length - 1 && l === "")).length;
}

async function verifyEvidence(sessionFile, nonce, jobId, startLine) {
  const script = [
    "import json, sys",
    `sys.path.insert(0, ${JSON.stringify(REPO)})`,
    "from tools.prime_resume_evidence import verify_resume_events",
    `print(json.dumps(verify_resume_events(${JSON.stringify(sessionFile)}, nonce=${JSON.stringify(nonce)}, expected_job_id=${JSON.stringify(jobId)}, start_line=${startLine}), ensure_ascii=False))`,
  ].join("\n");
  const result = await run(PY, ["-X", "utf8", "-c", script], { timeout: 60_000 });
  if (result.code !== 0) {
    throw new Error(result.stderr || result.stdout || "evidence verifier failed");
  }
  return parseJsonLine(result.stdout);
}

export async function runContentStudioResumePrime({ projectId } = {}) {
  const progressPath =
    process.env.CONTENT_STUDIO_RESUME_PROGRESS ||
    "C:\\ContentStudio\\reports\\pi-persistent-prime-handoff-continuity-v1\\PI_EXTENSION_E2E_PROGRESS.jsonl";
  const tick = (obj) => {
    const line = `${JSON.stringify({ at: new Date().toISOString(), ...obj })}\n`;
    process.stderr.write(line);
    try {
      writeFileSync(progressPath, line, { flag: "a", encoding: "utf8" });
    } catch {}
  };
  tick({ phase: "start", projectId: projectId || null });
  const request = await gateway("prepare-resume", projectId);
  tick({ phase: "prepare_done", session_file: request.session_file });
  const sessionFile = String(request.session_file || "");
  const sessionDir = String(request.session_dir || "");
  const agentDir = String(request.agent_dir || "");
  const skillPath = String(request.skill_path || join(REPO, "integrations", "prime-om-adapter"));
  const kernelPython = String(request.kernel_python || DEFAULT_KERNEL);
  if (!sessionFile.toLowerCase().endsWith(".jsonl")) {
    throw new Error("prepare-resume did not return a full Prime .jsonl session_file");
  }
  if (process.env.CONTENT_STUDIO_EVIDENCE_JOB_ID) {
    throw new Error(
      "CONTENT_STUDIO_EVIDENCE_JOB_ID is forbidden; evidence job_id must equal request.project_id",
    );
  }
  const nonce = `resume-nonce-${randomBytes(8).toString("hex")}`;
  const startLine = countLines(sessionFile);
  const jobId = String(request.project_id);
  const adapterSrc = join(REPO, "integrations", "prime-om-adapter", "src");
  const pyLines = [
    "import json, os, sys",
    "os.environ['OM_PRIME_ADAPTER_ROOT']=r'C:\\ContentStudio'",
    `sys.path.insert(0, r'${adapterSrc}')`,
    `sys.path.insert(0, r'${REPO}')`,
    "from om_prime_adapter import build_context_variables, reload_context",
    `ledger=build_context_variables(${JSON.stringify(jobId)})`,
    "reloaded=reload_context(ledger)",
    "payload={'nonce': " +
      JSON.stringify(nonce) +
      ", 'job_id': ledger.get('job_id'), 'variable_names': sorted(ledger.get('variables', dict())), 'reload_context': True, 'om_job_ref': (ledger.get('variables') or dict()).get('om_job_ref')}",
    "print(json.dumps(payload, ensure_ascii=False))",
  ];
  const prompt = [
    "You are resuming a project-bound Content Studio Prime session.",
    "Call the ipython tool exactly once with this code, then stop:",
    ...pyLines,
    "Do not start assets, H3, or rendering.",
  ].join("\n");

  const primeArgs = [
    PRIME_CLI_JS,
    "-p",
    "--provider",
    "bailian",
    "--model",
    "qwen3.8-max",
    "--thinking",
    "low",
    "--cwd",
    REPO,
    "--skill",
    skillPath,
    "--no-extensions",
    "--no-prompt-templates",
    "--no-context-files",
    "--session-dir",
    sessionDir,
    "--resume",
    sessionFile,
    "--",
    prompt,
  ];
  const joined = primeArgs.join(" ");
  if (/(^|\s)--no-session(\s|$)/.test(joined) || /(^|\s)--no-tools(\s|$)/.test(joined)) {
    throw new Error("forbidden fake-resume flags present");
  }
  const env = {
    ...process.env,
    OM_PRIME_ADAPTER_ROOT: process.env.OM_PRIME_ADAPTER_ROOT ?? "C:\\ContentStudio",
    OPENMONTAGE_PROJECTS_DIR: process.env.OPENMONTAGE_PROJECTS_DIR ?? "C:\\ContentStudio\\jobs",
    PRIME_AGENT_KERNEL_PYTHON: kernelPython,
  };
  if (agentDir) env.PRIME_AGENT_CODING_AGENT_DIR = agentDir;

  tick({ phase: "prime_spawn", thinking: "low", timeout_ms: 180000 });
  console.error(JSON.stringify({ phase: "prepare_done", session_file: sessionFile, kernel_python: kernelPython }));
  const prime = await run("node", primeArgs, { env, timeout: 180_000 });
  tick({ phase: "prime_done", code: prime.code, stdout_len: prime.stdout.length, stderr_len: prime.stderr.length });
  console.error(JSON.stringify({ phase: "prime_done", code: prime.code, stdout_len: prime.stdout.length, stderr_len: prime.stderr.length }));
  if (prime.code !== 0) {
    throw new Error(`Prime persistent resume failed: ${prime.stderr || prime.stdout}`);
  }
  const evidence = await verifyEvidence(sessionFile, nonce, jobId, startLine);
  tick({ phase: "evidence_done", status: evidence.status, reason: evidence.reason });
  console.error(JSON.stringify({ phase: "evidence_done", status: evidence.status, reason: evidence.reason }));
  if (evidence.status !== "PASS") {
    throw new Error(`Mechanical resume evidence failed: ${evidence.reason}`);
  }
  const ack = {
    status: "PRIME_OM_RESUME_ACCEPTED",
    project_id: request.project_id,
    checkpoint_sha256: request.checkpoint_sha256,
    next_stage: request.next_stage,
    session_file: request.session_file,
    resumed: true,
    fake_json_echo: false,
    evidence_line_range_1based: evidence.evidence_line_range_1based,
    nonce,
  };
  const receipt = await gateway("record-resume", projectId, [
    "--request-id",
    String(request.request_id),
    "--prime-response",
    JSON.stringify(ack),
    "--evidence-json",
    JSON.stringify(evidence),
  ]);
  return {
    request,
    evidence,
    receipt,
    nonce,
    kernel_python: kernelPython,
    argv_sha256: createHash("sha256").update(joined).digest("hex"),
    forbidden_flags_absent: true,
  };
}

async function main() {
  const args = process.argv.slice(2);
  let projectId;
  let outPath = null;
  for (let i = 0; i < args.length; i += 1) {
    if (args[i] === "--project-id") projectId = args[i + 1];
    if (args[i] === "--out") outPath = args[i + 1];
  }
  try {
    const result = await runContentStudioResumePrime({ projectId });
    const text = JSON.stringify({ status: "PASS", ...result }, null, 2);
    if (outPath) {
      mkdirSync(dirname(outPath), { recursive: true });
      writeFileSync(outPath, `${text}\n`, "utf8");
    }
    console.log(text);
    process.exit(0);
  } catch (err) {
    const payload = { status: "FAIL", error: String(err && err.message ? err.message : err) };
    console.error(JSON.stringify(payload, null, 2));
    if (outPath) writeFileSync(outPath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
    process.exit(1);
  }
}

const selfPath = fileURLToPath(import.meta.url);
if (process.argv[1] && resolve(process.argv[1]) === resolve(selfPath)) {
  main();
}
