/** Process-free spec-v0.5 reading fields; recorded evidence never runs checks. */
import { createHash } from "node:crypto";
import { readFileSync, readdirSync, existsSync, statSync, realpathSync } from "node:fs";
import { join, relative, resolve, isAbsolute, basename, dirname } from "node:path";
import { auditFile } from "./index.mjs";

const MAX_FILE_BYTES = 4 * 1024 * 1024;
const MAX_TOTAL_BYTES = 32 * 1024 * 1024;
const VERSIONS = Object.freeze([1, 2, 3, 4, 5].map(i => `spec-v0.${i}`));
const EVENTS = new Set(["session.start", "session.requirement", "session.finish", "session.finish.refused"]);
const CHECK_TYPES = new Set(["file_exists", "file_contains", "path_moved", "frontmatter", "glob_count", "command", "http_probe", "git_state"]);
export const readerCapabilities = Object.freeze({
  spec_versions: VERSIONS, integrity: "hash-chain",
  scope: "recorded requirements and receipt manifest", current_execution: "not performed",
  processes: false, network: false, test_adequacy: "not assessed",
  origin_authentication: "not established",
});
const sha = value => createHash("sha256").update(value).digest("hex");

function confined(root, path) {
  const actual = existsSync(path) ? realpathSync(path) : resolve(path);
  const rel = relative(root, actual);
  if (rel === ".." || rel.startsWith(`..${process.platform === "win32" ? "\\" : "/"}`) || isAbsolute(rel)) {
    throw new Error("receipt escapes workspace");
  }
  return actual;
}

function strictJson(text) {
  const value = JSON.parse(text);
  // JSON.parse accepts duplicate keys. Reader semantics must reject them.
  const tokens = text.match(/"(?:\\.|[^"\\])*"|[{}\[\]:,]/g) || [];
  const stack = [];
  for (let i = 0; i < tokens.length; i++) {
    const token = tokens[i];
    if (token === "{") stack.push(new Set());
    else if (token === "[") stack.push(null);
    else if (token === "}" || token === "]") stack.pop();
    else if (token.startsWith('"') && tokens[i + 1] === ":" && stack.at(-1)) {
      const key = JSON.parse(token);
      if (stack.at(-1).has(key)) throw new Error("duplicate JSON key");
      stack.at(-1).add(key);
    }
  }
  return value;
}

function pythonJson(value) {
  if (Array.isArray(value)) return `[${value.map(pythonJson).join(", ")}]`;
  if (value !== null && typeof value === "object") {
    return `{${Object.keys(value).sort().map(k => `${pythonJson(k)}: ${pythonJson(value[k])}`).join(", ")}}`;
  }
  return JSON.stringify(value).replace(/[\u007f-\uffff]/g, c =>
    `\\u${c.charCodeAt(0).toString(16).padStart(4, "0")}`);
}

export function inspectSession(workspace, session) {
  const result = {
    integrity: "YELLOW", scope: readerCapabilities.scope, spec_coverage: "supported_reading_fields",
    manifest: "absent", freshness: "open_or_absent", historical_outcome: "absent",
    recorded_outcome: "UNVERIFIED", current_execution: "not performed", current_outcome: "UNVERIFIED",
    requirement_count: 0, capabilities: { ...readerCapabilities, spec_versions: [...VERSIONS] },
  };
  try {
    if (typeof session !== "string" || !session.trim()) throw new Error("session missing");
    const root = realpathSync(workspace);
    const base = confined(root, join(root, ".showwork"));
    if (!existsSync(base)) return result;
    let paths = readdirSync(base).filter(n => /^claims-.*\.jsonl$/.test(n)).sort().map(n => join(base, n));
    if (existsSync(join(base, "sessions.jsonl"))) paths.push(join(base, "sessions.jsonl"));
    for (const name of ["claims", "sessions"]) {
      const folder = confined(root, join(base, name));
      if (existsSync(folder)) paths.push(...readdirSync(folder).filter(n => n.endsWith(".jsonl")).sort().map(n => join(folder, n)));
    }
    if (paths.length > 1024) throw new Error("too many receipt files");
    const claims = [], events = [], audits = [], files = {};
    let total = 0;
    for (let path of paths) {
      path = confined(root, path);
      const size = statSync(path).size;
      if (size > MAX_FILE_BYTES || (total += size) > MAX_TOTAL_BYTES) throw new Error("receipt exceeds reader bounds");
      const bytes = readFileSync(path);
      if (bytes.length > MAX_FILE_BYTES) throw new Error("receipt exceeds reader bounds");
      const text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
      const rows = text.split(/\r?\n/).map(line => line.trim()).filter(line => line && !line.startsWith("#")).map(strictJson);
      if (rows.some(row => !row || Array.isArray(row) || typeof row !== "object")) throw new Error("non-object receipt row");
      audits.push(auditFile(path, false, text));
      const selected = rows.filter(row => row.session === session || row.retracts?.session === session);
      if (basename(dirname(path)) === "sessions" || basename(path) === "sessions.jsonl") events.push(...selected);
      else {
        claims.push(...selected);
        if (selected.length) files[relative(root, path).replaceAll("\\", "/")] = sha(Buffer.from(bytes.toString("utf8").replaceAll("\r\n", "\n")));
      }
    }
    events.sort((a, b) => String(a.ts || "").localeCompare(String(b.ts || "")));
    result.integrity = audits.some(row => row.verdict === "RED") ? "RED" :
      !audits.length || audits.some(row => row.verdict !== "GREEN") ? "YELLOW" : "GREEN";
    const unsupported = [...events, ...claims].some(row =>
      (row.spec_version != null && !VERSIONS.includes(row.spec_version)) ||
      (row.required_semantics != null && (typeof row.required_semantics === "object" ?
        Object.keys(row.required_semantics).length > 0 : !!row.required_semantics)));
    if (unsupported || events.some(row => !EVENTS.has(row.event))) result.spec_coverage = "unsupported";
    const requirements = events.filter(row => row.event === "session.requirement");
    if (requirements.some(row => !row.check || typeof row.check !== "object" ||
        !CHECK_TYPES.has(row.check.type) || !["behavior", "artifact"].includes(row.scope) ||
        row.scope === "behavior" && row.check.type !== "command") ||
        claims.some(row => row.check && typeof row.check === "object" && !CHECK_TYPES.has(row.check.type))) {
      result.spec_coverage = "unsupported";
    }
    result.requirement_count = requirements.length;
    const lifecycle = events.filter(row => ["session.start", "session.finish", "session.finish.refused"].includes(row.event));
    const latest = lifecycle.at(-1) || {};
    const close = lifecycle.filter(row => row.event === "session.finish").at(-1);
    const expected = { claims: files, requirement_count: requirements.length, requirements_sha256: sha(pythonJson(requirements)) };
    if (close) {
      if ("receipt_manifest" in close) result.manifest = pythonJson(close.receipt_manifest) === pythonJson(expected) ? "matches" : "mismatch";
      result.historical_outcome = close.outcome?.verdict || "unverified";
    }
    if (latest.event === "session.finish.refused") result.historical_outcome = "refused";
    result.freshness = close && latest.event === "session.start" ? "reopened" :
      latest.event === "session.finish" ? "recorded_close" : "open_or_absent";
    if (result.spec_coverage !== "unsupported" && result.integrity === "GREEN" && result.manifest === "matches" &&
        result.freshness === "recorded_close" && close?.status === "ok" && close.completion_scope === "outcome" &&
        !close.verify_bypassed && result.historical_outcome === "VERIFIED") result.recorded_outcome = "VERIFIED";
    return result;
  } catch {
    return { ...result, integrity: "unknown", spec_coverage: "unreadable", recorded_outcome: "UNVERIFIED",
      reason: "receipt unreadable or outside reader bounds" };
  }
}
