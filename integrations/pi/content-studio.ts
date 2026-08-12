import { StringEnum, Type } from "@earendil-works/pi-ai";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { spawn } from "node:child_process";

const REPO = process.env.CONTENT_STUDIO_OM_REPO ?? "C:\\ContentStudio\\repos\\OpenMontage";
const GATEWAY = `${REPO}\\tools\\content_studio_gateway.py`;
const QDRANT_EXE = process.env.CONTENT_STUDIO_QDRANT_EXE ?? "C:\\ContentStudio\\tools\\qdrant\\v1.17.1\\qdrant.exe";
const QDRANT_CONFIG = process.env.CONTENT_STUDIO_QDRANT_CONFIG ?? "C:\\ContentStudio\\runtime\\qdrant\\config.yaml";
const QDRANT_CWD = process.env.CONTENT_STUDIO_QDRANT_CWD ?? "C:\\ContentStudio\\runtime\\qdrant";
const QDRANT_COLLECTION = "nf_stock_footage_v1";
const PRIME_CLI_JS = process.env.PRIME_AGENT_CLI_JS
  ?? `${process.env.APPDATA}\\npm\\node_modules\\prime-agent\\dist\\bundle\\cli.js`;

type GatewayResult = Record<string, unknown>;

function textResult(payload: GatewayResult) {
  return {
    content: [{ type: "text" as const, text: JSON.stringify(payload, null, 2) }],
    details: payload,
  };
}

export default function contentStudioExtension(pi: ExtensionAPI) {
  async function qdrantHealth(): Promise<GatewayResult | null> {
    try {
      const response = await fetch(`http://127.0.0.1:6333/collections/${QDRANT_COLLECTION}`, {
        signal: AbortSignal.timeout(2_000),
      });
      if (!response.ok) return null;
      const payload = (await response.json()) as { status?: string; result?: { points_count?: number } };
      if (payload.status !== "ok") return null;
      return {
        status: "PASS",
        collection: QDRANT_COLLECTION,
        points_count: payload.result?.points_count,
        endpoint: "http://127.0.0.1:6333",
      };
    } catch {
      return null;
    }
  }

  async function ensureQdrant(): Promise<GatewayResult> {
    const current = await qdrantHealth();
    if (current) return { ...current, action: "already_running" };
    const process = spawn(
      QDRANT_EXE,
      ["--config-path", QDRANT_CONFIG, "--disable-telemetry"],
      { cwd: QDRANT_CWD, detached: true, stdio: "ignore", windowsHide: true },
    );
    process.unref();
    for (let attempt = 0; attempt < 60; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 500));
      const health = await qdrantHealth();
      if (health) return { ...health, action: "started_by_windows_pi" };
    }
    throw new Error("Windows Qdrant did not become ready within 30 seconds");
  }

  async function runGateway(
    command: string,
    projectId?: string,
    commandOptions: string[] = [],
    signal?: AbortSignal,
  ): Promise<GatewayResult> {
    const args = [
      "-X",
      "utf8",
      GATEWAY,
      ...(projectId ? ["--project-id", projectId] : []),
      command,
      ...commandOptions,
    ];
    const result = await pi.exec(
      "python",
      args,
      { signal, timeout: 120_000 },
    );
    const output = result.stdout.trim();
    let payload: GatewayResult;
    try {
      payload = JSON.parse(output) as GatewayResult;
    } catch {
      throw new Error(`Content Studio gateway returned invalid JSON: ${result.stderr || output}`);
    }
    if (result.code !== 0 || payload.status === "ERROR") {
      throw new Error(String(payload.error || result.stderr || "Content Studio gateway failed"));
    }
    return payload;
  }

  pi.registerTool({
    name: "content_studio_media_status",
    label: "Content Studio Media Runtime Status",
    description:
      "Start or verify the Windows-local Qdrant media index. It never contacts Mac and does not change OM project state.",
    promptSnippet: "Check the Windows-local Content Studio media library and vector index",
    promptGuidelines: [
      "Use this tool when Alan asks whether the local media library or stock search is ready.",
      "Do not claim Windows is canonical; promotion requires two real stock-media projects and Alan approval.",
    ],
    parameters: Type.Object({}),
    async execute() {
      return textResult(await ensureQdrant());
    },
  });

  pi.registerTool({
    name: "content_studio_open_current",
    label: "Open Current Content Studio Project",
    description:
      "Recover the current OpenMontage project from canonical checkpoints and show its Sceneplan Gate as eight separate columns: image result, visual/action intent, exact prompt, dialogue, duration, and sound. Never asks the user for a path.",
    promptSnippet: "Open the current Content Studio project and show its canonical Sceneplan Gate",
    promptGuidelines: [
      "Use content_studio_open_current whenever Alan asks to open the current Content Studio project or view the Sceneplan Gate; do not ask him for project paths or prompts.",
      "Present image result, visual/action intent, and exact provider prompt as separate fields so Alan can diagnose intent, prompt, or generation errors.",
    ],
    parameters: Type.Object({
      projectId: Type.Optional(Type.String({ description: "Optional OM project ID; omit for the canonical current project" })),
    }),
    async execute(_toolCallId, params, signal) {
      return textResult(await runGateway("show-gate", params.projectId, [], signal));
    },
  });

  pi.registerTool({
    name: "content_studio_apply_sceneplan_decisions",
    label: "Apply Sceneplan Gate Decisions",
    description:
      "Persist Alan's explicit keep/change/merge/omit decisions into the canonical OM scene_plan and checkpoint. Uses a displayed checkpoint hash to reject stale decisions, archives the old artifact/checkpoint, and never starts production on a pending change.",
    promptSnippet: "Write Alan's keep/change/merge/omit decisions to the current OM Sceneplan Gate",
    promptGuidelines: [
      "Use content_studio_apply_sceneplan_decisions only after Alan explicitly decides cuts in Windows Pi.",
      "For change, preserve Alan's human-readable visual intent separately from the exact prompt; do not invent approval for undecided cuts.",
      "After every cut is keep, merge, or omit, call content_studio_resume_prime to prove the Pi to OM to Prime handoff without starting rendering in the entry smoke.",
    ],
    parameters: Type.Object({
      projectId: Type.Optional(Type.String()),
      expectedCheckpointSha256: Type.String({ description: "checkpoint.sha256 returned by content_studio_open_current" }),
      decisions: Type.Array(
        Type.Object({
          cut_id: Type.String(),
          decision: StringEnum(["keep", "change", "merge", "omit"] as const),
          note: Type.Optional(Type.String()),
          visual_intent: Type.Optional(Type.String()),
          prompt: Type.Optional(Type.String()),
          merge_target_id: Type.Optional(Type.String()),
        }),
        { minItems: 1 },
      ),
    }),
    async execute(_toolCallId, params, signal) {
      const options = [
        "--expected-checkpoint-sha256",
        params.expectedCheckpointSha256,
        "--decisions-json",
        JSON.stringify(params.decisions),
      ];
      return textResult(await runGateway("apply-sceneplan", params.projectId, options, signal));
    },
  });

  pi.registerTool({
    name: "content_studio_resume_prime",
    label: "Resume Persistent Prime From OM Checkpoint",
    description:
      "After a Windows Pi Sceneplan approval, resume the project-bound persistent Prime .jsonl session, mechanically verify IPython revival from JSONL events, and record a receipt. Never uses --no-session/--no-tools fake JSON echo. Does not start assets or rendering.",
    promptSnippet: "Resume the persistent Prime session for the approved OM checkpoint and record a receipt",
    promptGuidelines: [
      "Use content_studio_resume_prime only when the Sceneplan Gate is fully approved; it must remain bound to the OM checkpoint hash and a project-level SESSION_POINTER.json.",
      "If prepare-resume fails because no project pointer exists, tell Alan a Director session must be created for this project first; do not invent a JSON-only acknowledgement.",
    ],
    parameters: Type.Object({
      projectId: Type.Optional(Type.String()),
    }),
    async execute(_toolCallId, params, signal) {
      const runner = `${REPO}\\tools\\run_content_studio_resume_prime.py`;
      const py =
        process.env.CONTENT_STUDIO_PYTHON ??
        "C:\\ContentStudio\\runtime\\OpenMontage-test-venv\\Scripts\\python.exe";
      const args = ["-X", "utf8", runner];
      if (params.projectId) {
        args.push("--project-id", params.projectId);
      }
      const env: Record<string, string> = {
        ...process.env,
        CONTENT_STUDIO_OM_REPO: REPO,
        CONTENT_STUDIO_PYTHON: py,
        CONTENT_STUDIO_PRIME_KERNEL_PYTHON:
          process.env.CONTENT_STUDIO_PRIME_KERNEL_PYTHON ??
          "C:\\ContentStudio\\runtime\\Prime-kernel-venv\\Scripts\\python.exe",
        PRIME_AGENT_KERNEL_PYTHON:
          process.env.PRIME_AGENT_KERNEL_PYTHON ??
          process.env.CONTENT_STUDIO_PRIME_KERNEL_PYTHON ??
          "C:\\ContentStudio\\runtime\\Prime-kernel-venv\\Scripts\\python.exe",
        OM_PRIME_ADAPTER_ROOT: process.env.OM_PRIME_ADAPTER_ROOT ?? "C:\\ContentStudio",
        OPENMONTAGE_PROJECTS_DIR: process.env.OPENMONTAGE_PROJECTS_DIR ?? "C:\\ContentStudio\\jobs",
      };
      const result = await pi.exec(py, args, { signal, timeout: 300_000, env });
      if (result.code !== 0) {
        throw new Error(`content_studio_resume_prime failed: ${result.stderr || result.stdout}`);
      }
      const output = result.stdout.trim();
      const jsonStart = output.lastIndexOf("{");
      const payload = JSON.parse(jsonStart >= 0 ? output.slice(jsonStart) : output) as GatewayResult;
      if (payload.status === "FAIL" || payload.status === "ERROR") {
        throw new Error(String(payload.error || "content_studio_resume_prime failed"));
      }
      return textResult(payload);
    },
  });

  pi.registerTool({
    name: "content_studio_status",
    label: "Content Studio Status",
    description: "Re-read the canonical OM checkpoint, persisted cut decisions, and Prime resume receipt after a Pi restart.",
    promptSnippet: "Reopen the current OM project and verify persisted decisions after restart",
    parameters: Type.Object({
      projectId: Type.Optional(Type.String()),
    }),
    async execute(_toolCallId, params, signal) {
      return textResult(await runGateway("status", params.projectId, [], signal));
    },
  });
}
