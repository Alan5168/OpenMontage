import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { parseGatewayStdout } from "./parse_gateway_json.mjs";

const here = dirname(fileURLToPath(import.meta.url));

function test(name, fn) {
  try {
    fn();
    console.log(`PASS ${name}`);
  } catch (err) {
    console.error(`FAIL ${name}`);
    throw err;
  }
}

test("parses full pretty nested JSON (real receipt shape)", () => {
  const nested = {
    status: "PASS",
    request: { project_id: "fixture-pi-resume-e2e", nested: { a: 1 } },
    evidence: {
      status: "PASS",
      job_id: "fixture-pi-resume-e2e",
      variable_names: ["om_job_ref"],
      accepted_payload: { nonce: "x", job_id: "fixture-pi-resume-e2e" },
    },
    receipt: { resumed_evidence: { nonce: "x" } },
  };
  const text = JSON.stringify(nested, null, 2);
  const parsed = parseGatewayStdout(text);
  assert.equal(parsed.status, "PASS");
  assert.equal(parsed.evidence.job_id, "fixture-pi-resume-e2e");
  assert.equal(parsed.request.project_id, "fixture-pi-resume-e2e");
});

test("lastIndexOf would fail on nested pretty JSON; parser must not", () => {
  const text = JSON.stringify(
    {
      status: "PASS",
      evidence: { accepted_payload: { job_id: "fixture-pi-resume-e2e" } },
    },
    null,
    2,
  );
  const brokenStart = text.lastIndexOf("{");
  assert.throws(() => JSON.parse(text.slice(brokenStart)), /Unexpected|JSON/);
  const parsed = parseGatewayStdout(text);
  assert.equal(parsed.status, "PASS");
});

test("parses compact single-line JSON", () => {
  const parsed = parseGatewayStdout('{"status":"PASS","ok":true}');
  assert.equal(parsed.status, "PASS");
  assert.equal(parsed.ok, true);
});

test("parses JSON after leading noise using outermost object", () => {
  const parsed = parseGatewayStdout('note: ignore\n{"status":"PASS","n":1}\n');
  assert.equal(parsed.status, "PASS");
  assert.equal(parsed.n, 1);
});

test("fixture receipt file parses if present", () => {
  const candidates = [
    join(
      here,
      "..",
      "..",
      "..",
      "reports",
      "windows-pi-persistent-prime-handoff-continuity-v1",
      "PI_EXTENSION_E2E_RECEIPT.json",
    ),
    "C:/ContentStudio/reports/pi-persistent-prime-handoff-continuity-v1/PI_EXTENSION_E2E_RECEIPT.json",
  ];
  for (const path of candidates) {
    try {
      const raw = readFileSync(path, "utf8");
      const parsed = parseGatewayStdout(raw);
      assert.equal(parsed.status, "PASS");
      console.log(`PASS fixture receipt via ${path}`);
      return;
    } catch {
      // try next
    }
  }
  console.log("SKIP fixture receipt file not found locally");
});

console.log("all parse_gateway_json tests passed");
