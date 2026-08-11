import { StringEnum, Type } from "@earendil-works/pi-ai";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const REPO = process.env.CONTENT_STUDIO_OM_REPO ?? "C:\\ContentStudio\\repos\\OpenMontage";
const GATEWAY = `${REPO}\\tools\\content_studio_gateway.py`;

type GatewayResult = Record<string, unknown>;

function textResult(payload: GatewayResult) {
  return {
    content: [{ type: "text" as const, text: JSON.stringify(payload, null, 2) }],
    details: payload,
  };
}

export default function contentStudioExtension(pi: ExtensionAPI) {
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
    label: "Resume Prime From OM Checkpoint",
    description:
      "After a Windows Pi Sceneplan approval, build an OM-bound resume request, obtain a real Bailian qwen3.8-max acknowledgement from Prime Agent, and record a receipt. The entry smoke deliberately does not start assets or rendering.",
    promptSnippet: "Resume Prime from the approved canonical OM checkpoint and record a receipt",
    promptGuidelines: [
      "Use content_studio_resume_prime only when the Sceneplan Gate is fully approved; it must remain bound to the OM checkpoint hash.",
    ],
    parameters: Type.Object({
      projectId: Type.Optional(Type.String()),
    }),
    async execute(_toolCallId, params, signal) {
      const request = await runGateway("prepare-resume", params.projectId, [], signal);
      const prompt = [
        "You are Windows Prime Agent receiving a resume request from OpenMontage through Windows Pi.",
        "Acknowledge the checkpoint only. Do not call tools, generate assets, or start rendering.",
        "Return exactly one JSON object and no markdown with these fields:",
        "status=PRIME_OM_RESUME_ACCEPTED, project_id, checkpoint_sha256, next_stage.",
        `REQUEST=${JSON.stringify(request)}`,
      ].join("\n");
      const prime = await pi.exec(
        "prime-agent",
        [
          "-p",
          "--no-tools",
          "--no-context-files",
          "--no-session",
          "--provider",
          "bailian",
          "--model",
          "qwen3.8-max",
          "--thinking",
          "high",
          "--cwd",
          REPO,
          "--",
          prompt,
        ],
        { signal, timeout: 180_000 },
      );
      if (prime.code !== 0) {
        throw new Error(`Prime resume acknowledgement failed: ${prime.stderr || prime.stdout}`);
      }
      const response = prime.stdout.trim();
      try {
        JSON.parse(response);
      } catch {
        throw new Error("Prime did not return the required strict JSON acknowledgement");
      }
      const receipt = await runGateway(
        "record-resume",
        params.projectId,
        [
          "--request-id",
          String(request.request_id),
          "--prime-response",
          response,
        ],
        signal,
      );
      return textResult(receipt);
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
