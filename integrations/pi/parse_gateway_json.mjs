/**
 * Parse stdout from Content Studio gateway / resume runners.
 * Prefer the full stdout JSON object. Never use lastIndexOf("{") —
 * nested pretty JSON would start at an inner object and fail.
 */

/**
 * @param {string} text
 * @returns {Record<string, unknown>}
 */
export function parseGatewayStdout(text) {
  const trimmed = String(text ?? "").trim();
  if (!trimmed) {
    throw new Error("empty gateway/resume stdout");
  }

  try {
    const full = JSON.parse(trimmed);
    if (full && typeof full === "object" && !Array.isArray(full)) {
      return full;
    }
  } catch {
    // fall through to outermost-object extraction
  }

  const start = trimmed.indexOf("{");
  if (start < 0) {
    throw new Error("no JSON object in stdout");
  }

  const slice = trimmed.slice(start);
  try {
    const fromFirst = JSON.parse(slice);
    if (fromFirst && typeof fromFirst === "object" && !Array.isArray(fromFirst)) {
      return fromFirst;
    }
  } catch {
    // balanced scan below
  }

  let depth = 0;
  let inString = false;
  let escape = false;
  for (let i = 0; i < slice.length; i += 1) {
    const ch = slice[i];
    if (inString) {
      if (escape) {
        escape = false;
      } else if (ch === "\\") {
        escape = true;
      } else if (ch === "\"") {
        inString = false;
      }
      continue;
    }
    if (ch === "\"") {
      inString = true;
      continue;
    }
    if (ch === "{") {
      depth += 1;
    } else if (ch === "}") {
      depth -= 1;
      if (depth === 0) {
        return JSON.parse(slice.slice(0, i + 1));
      }
    }
  }

  throw new Error("Unable to parse gateway/resume stdout as JSON object");
}
