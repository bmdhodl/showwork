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
const IGNORE_SEMANTIC = "snapshot-exclusions-v1";
const IGNORE_FORMAT = "relative-glob-v1";
export const readerCapabilities = Object.freeze({
  spec_versions: VERSIONS, integrity: "hash-chain",
  scope: "recorded requirements and receipt manifest", current_execution: "not performed",
  processes: false, network: false, test_adequacy: "not assessed",
  origin_authentication: "not established",
  required_semantics: Object.freeze([IGNORE_SEMANTIC]),
});
const sha = value => createHash("sha256").update(value).digest("hex");

function sessionStem(original) {
  const raw = original.trim();
  if (!raw || raw === "." || raw === "..") throw new Error("unsafe session");
  let cleaned = raw.replace(/[^a-zA-Z0-9_.-]/gu, "-").replace(/^[.-]+|[.-]+$/g, "").replace(/-{2,}/g, "-");
  const reserved = /^(?:con|prn|aux|nul|com[1-9]|lpt[1-9])$/;
  if (reserved.test(cleaned.toLowerCase()) || reserved.test(cleaned.split(".")[0].toLowerCase())) cleaned = `sess-${cleaned}`;
  const lossy = cleaned !== raw || [...raw].length > 120 || original !== raw || cleaned !== cleaned.toLowerCase() || cleaned.toLowerCase().startsWith("h-");
  if (lossy) {
    const prefix = `h-${sha(original).slice(0, 10)}-`;
    const base = cleaned.toLowerCase().slice(0, 120 - prefix.length).replace(/[.-]+$/g, "");
    cleaned = base ? prefix + base : prefix.slice(0, -1);
  }
  if (!cleaned || !/^[a-zA-Z0-9_.-]+$/.test(cleaned)) throw new Error("unsafe session");
  return cleaned;
}

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

function unicodeOrder(a, b) {
  const left = [...a], right = [...b];
  for (let i = 0; i < Math.min(left.length, right.length); i++) {
    const delta = left[i].codePointAt(0) - right[i].codePointAt(0);
    if (delta) return delta;
  }
  return left.length - right.length;
}

function compactPythonJson(value) {
  if (Array.isArray(value)) return `[${value.map(compactPythonJson).join(",")}]`;
  if (value !== null && typeof value === "object") {
    return `{${Object.keys(value).sort(unicodeOrder).map(k => `${compactPythonJson(k)}:${compactPythonJson(value[k])}`).join(",")}}`;
  }
  return JSON.stringify(value).replace(/[\u007f-\uffff]/g, c =>
    `\\u${c.charCodeAt(0).toString(16).padStart(4, "0")}`);
}

function componentMatches(value, pattern) {
  // Bounded component wildcard matching without backtracking regex execution.
  const chars = [...value], globs = [...pattern];
  let i = 0, j = 0, star = -1, retry = 0;
  while (i < chars.length) {
    if (j < globs.length && (globs[j] === "?" || globs[j] === chars[i])) { i++; j++; }
    else if (globs[j] === "*") { star = j++; retry = i; }
    else if (star >= 0) { j = star + 1; i = ++retry; }
    else return false;
  }
  while (globs[j] === "*") j++;
  return j === globs.length;
}

function exclusionScope(meta) {
  if (!meta || typeof meta !== "object" || Array.isArray(meta)) throw new Error("snapshot metadata missing");
  if (!("ignore_format" in meta) && !("ignore_patterns" in meta)) return {};
  const patterns = meta.ignore_patterns;
  if (meta.ignore_format !== IGNORE_FORMAT || !Array.isArray(patterns) || !patterns.length || patterns.length > 32 ||
      !Number.isInteger(meta.count) || meta.count < 0 || meta.count > 50000 ||
      typeof meta.sha256 !== "string" || !/^[0-9a-f]{64}$/.test(meta.sha256) ||
      compactPythonJson(patterns) !== compactPythonJson([...new Set(patterns)].sort(unicodeOrder))) throw new Error("snapshot exclusions invalid");
  for (const pattern of patterns) {
    if (typeof pattern !== "string" || ![...pattern].length || [...pattern].length > 240 || /[\x00-\x1f\x7f\\:\[\]]/u.test(pattern)) throw new Error("invalid relative glob");
    const parts = pattern.split("/");
    if (parts.some(part => ["", ".", ".."].includes(part)) ||
        parts.some((part, i) => part.includes("**") && !(part === "**" && i === parts.length - 1)) ||
        pattern === "**" || parts.some(part => part !== "**" && [".git", ".showwork"].some(name => componentMatches(name, part.toLowerCase())))) throw new Error("invalid relative glob");
  }
  return { ignore_format: IGNORE_FORMAT, ignore_patterns: patterns };
}

function excludedFile(path, patterns) {
  const parts = path.split("/");
  return patterns.some(pattern => {
    const wanted = pattern.split("/"), recursive = wanted.at(-1) === "**";
    const prefix = recursive ? wanted.slice(0, -1) : wanted;
    return (recursive ? parts.length >= prefix.length : parts.length === prefix.length) &&
      prefix.every((glob, i) => componentMatches(parts[i], glob));
  });
}

function readExclusions(root, base, session, events, total) {
  const starts = events.filter(row => row.event === "session.start");
  const scoped = starts.some(row => row.required_semantics?.includes?.(IGNORE_SEMANTIC) ||
    row.tree_snapshot && ("ignore_format" in row.tree_snapshot || "ignore_patterns" in row.tree_snapshot));
  if (!scoped) return { ignore_patterns: [] };
  const meta = starts[0]?.tree_snapshot, scope = exclusionScope(meta);
  if (!scope.ignore_patterns || starts.some(row => compactPythonJson(row.tree_snapshot) !== compactPythonJson(meta) ||
      compactPythonJson(row.required_semantics) !== compactPythonJson([IGNORE_SEMANTIC]))) throw new Error("snapshot scope changed across starts");
  const path = confined(root, join(base, "snapshots", `${sessionStem(session)}.json`));
  if (statSync(path).size > MAX_FILE_BYTES || total + statSync(path).size > MAX_TOTAL_BYTES) throw new Error("snapshot exceeds reader bounds");
  const bytes = readFileSync(path);
  if (bytes.length > MAX_FILE_BYTES || total + bytes.length > MAX_TOTAL_BYTES) throw new Error("snapshot exceeds reader bounds");
  const payload = strictJson(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
  const files = payload?.files;
  if (!files || typeof files !== "object" || Array.isArray(files) || Object.keys(files).length > 50000 ||
      compactPythonJson(exclusionScope(payload)) !== compactPythonJson(scope) ||
      !Number.isInteger(meta.count) || !Number.isInteger(payload.count) ||
      meta.count !== Object.keys(files).length || payload.count !== meta.count ||
      Object.entries(files).some(([name, digest]) => !name || /[\\:]/u.test(name) ||
        name.split("/").some(part => ["", ".", ".."].includes(part)) ||
        typeof digest !== "string" || !/^[0-9a-f]{64}$/.test(digest) || excludedFile(name, scope.ignore_patterns))) throw new Error("snapshot sidecar invalid");
  const digest = sha(compactPythonJson({ files, ...scope }));
  if (meta.sha256 !== digest || payload.sha256 !== digest) throw new Error("snapshot digest mismatch");
  return scope;
}

export function inspectSession(workspace, session) {
  const result = {
    integrity: "YELLOW", scope: readerCapabilities.scope, spec_coverage: "supported_reading_fields",
    manifest: "absent", freshness: "open_or_absent", historical_outcome: "absent",
    recorded_outcome: "UNVERIFIED", current_execution: "not performed", current_outcome: "UNVERIFIED",
    requirement_count: 0, capabilities: { ...readerCapabilities, spec_versions: [...VERSIONS] },
    snapshot_scope: { ignore_patterns: [] },
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
    const streams = [], events = [], audits = [], files = {};
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
        streams.push({ path, rows: selected });
        if (selected.length) files[relative(root, path).replaceAll("\\", "/")] = sha(Buffer.from(bytes.toString("utf8").replaceAll("\r\n", "\n")));
      }
    }
    let current = join(base, "claims", `${sessionStem(session)}.jsonl`);
    const candidates = streams.filter(stream => basename(dirname(stream.path)) === "claims" && stream.rows.length);
    if (!existsSync(current) && candidates.length === 1) current = candidates[0].path;
    const others = streams.filter(stream => stream.path !== current && stream.rows.length);
    const firstTs = stream => String(stream.rows.find(row => typeof row.ts === "string" && row.ts)?.ts || "");
    others.sort((a, b) => firstTs(a) < firstTs(b) ? -1 : firstTs(a) > firstTs(b) ? 1 : 0);
    const claims = [...others.flatMap(stream => stream.rows), ...(streams.find(stream => stream.path === current)?.rows || [])];
    result.snapshot_scope = readExclusions(root, base, session, events, total);
    result.integrity = audits.some(row => row.verdict === "RED") ? "RED" :
      !audits.length || audits.some(row => row.verdict !== "GREEN") ? "YELLOW" : "GREEN";
    const unsupported = [...events, ...claims].some(row =>
      (row.spec_version != null && !VERSIONS.includes(row.spec_version)) ||
      (row.required_semantics != null && (typeof row.required_semantics === "object" ?
        Object.keys(row.required_semantics).length > 0 : !!row.required_semantics) &&
        !(events.includes(row) && row.event === "session.start" && compactPythonJson(row.required_semantics) === compactPythonJson([IGNORE_SEMANTIC]) && row.tree_snapshot)));
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
    return { ...result, integrity: "unknown", spec_coverage: "unreadable", recorded_outcome: "UNVERIFIED", snapshot_scope: null,
      reason: "receipt unreadable or outside reader bounds" };
  }
}
