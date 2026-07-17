/**
 * showwork-audit: reader-side implementation of the showwork ledger's
 * integrity chain (SPEC.md, spec-v0.2 "Integrity chain").
 *
 * Zero dependencies; node:crypto + node:fs only. This package audits chains
 * and reports verdicts. It re-executes NO checks - per the specification's
 * reader-only conformance clause, everything it does not re-verify is
 * reported, never silently skipped.
 *
 * Semantics mirror the reference implementation (src/showwork/audit.py);
 * the shared fixtures under tests/fixtures/chain/ hold both to the same
 * verdicts.
 */

import { createHash } from "node:crypto";
import { readFileSync, readdirSync, existsSync, statSync } from "node:fs";
import { join, basename } from "node:path";

const GENESIS_PREFIX = "showwork:genesis:";

/** SHA-256 hex of one record line's stripped content (EOL-agnostic). */
export function lineHash(line) {
  return createHash("sha256").update(line.trim(), "utf8").digest("hex");
}

/** Anchor for the first record of a ledger file. */
export function genesisHash(fileName) {
  return createHash("sha256").update(GENESIS_PREFIX + fileName, "utf8").digest("hex");
}

/**
 * Audit one ledger file's hash chain. A `prev` matching any earlier line (or
 * genesis) is accepted; one matching a non-immediate earlier line is a fork,
 * not a break. A `prev` matching no earlier line stays RED. With strict=true a
 * fork is RED. Mirrors src/showwork/audit.py; see docs/concurrency.md.
 * @param {string} filePath
 * @param {boolean} [strict]
 * @returns {{file: string, records: number, chained: number, pre_chain: number,
 *            forks: number, head: string|null, heads: string[],
 *            break_at: number|null, detail: string, verdict: string}}
 */
export function auditFile(filePath, strict = false) {
  const fileName = basename(filePath);
  const out = {
    file: fileName,
    records: 0,
    chained: 0,
    pre_chain: 0,
    forks: 0,
    head: null,
    heads: [],
    break_at: null,
    detail: "",
    verdict: "GREEN",
  };
  let text = readFileSync(filePath, "utf8");
  if (text.charCodeAt(0) === 0xfeff) text = text.slice(1); // BOM
  const genesis = genesisHash(fileName);
  const seen = new Set([genesis]); // genesis + every record line already seen
  const referenced = new Set(); // hashes used as some record's prev
  const recordHashes = []; // hash of every record line, in order
  let prevLine = null;
  let chainStarted = false;
  let lineNo = 0;
  for (const raw of text.split(/\r?\n/)) {
    lineNo += 1;
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    out.records += 1;
    const expected = prevLine !== null ? lineHash(prevLine) : genesis;
    let rec = null;
    try {
      rec = JSON.parse(line);
    } catch {
      rec = null;
    }
    const prev = rec && typeof rec === "object" ? rec.prev : undefined;
    if (prev !== undefined && prev !== null) {
      chainStarted = true;
      out.chained += 1;
      if (prev === expected) {
        // linear step
      } else if (seen.has(prev)) {
        // re-anchors to an earlier line (or a second genesis root): a fork.
        out.forks += 1;
        if (strict) {
          out.verdict = "RED";
          out.break_at = lineNo;
          out.detail = `fork at line ${lineNo}: prev ${String(prev).slice(0, 12)}... ` +
            `re-anchors to an earlier line; --strict forbids concurrent branches`;
          return out;
        }
      } else {
        out.verdict = "RED";
        out.break_at = lineNo;
        out.detail = `chain break at line ${lineNo}: prev is ${String(prev).slice(0, 12)}..., ` +
          `matches no earlier line (expected ${expected.slice(0, 12)}...)`;
        return out;
      }
      referenced.add(prev);
    } else {
      if (chainStarted) {
        out.verdict = "RED";
        out.break_at = lineNo;
        out.detail = `unchained record at line ${lineNo} after the chain started: ` +
          `append-only cannot be shown`;
        return out;
      }
      out.pre_chain += 1;
    }
    const h = lineHash(line);
    seen.add(h);
    recordHashes.push(h);
    prevLine = line;
  }
  if (prevLine !== null) out.head = lineHash(prevLine);
  if (out.chained) out.heads = recordHashes.filter((h) => !referenced.has(h));
  if (out.records === 0) {
    out.verdict = "YELLOW";
    out.detail = "empty ledger file: nothing to anchor";
  } else if (out.chained === 0) {
    out.verdict = "YELLOW";
    out.detail = `${out.records} record(s), none chained yet: ` +
      `integrity is unprovable until the first chained append`;
  } else {
    let detail = `intact: ${out.chained} chained record(s)` +
      (out.pre_chain ? `, ${out.pre_chain} pre-chain record(s) anchored` : "");
    if (out.forks) {
      detail += `; ${out.forks} fork(s) across ${out.heads.length} branch head(s)` +
        `; publish heads to anchor the tips`;
    }
    out.detail = detail;
  }
  return out;
}

/** Audit every ledger file under a project root's .showwork/ directory. */
export function auditRoot(root, strict = false) {
  const dir = join(root, ".showwork");
  const files = [];
  if (existsSync(dir) && statSync(dir).isDirectory()) {
    for (const name of readdirSync(dir).sort()) {
      if (/^claims-.*\.jsonl$/.test(name)) files.push(join(dir, name));
    }
    const sessions = join(dir, "sessions.jsonl");
    if (existsSync(sessions)) files.push(sessions);
  }
  const results = files.map((f) => auditFile(f, strict));
  let verdict = "GREEN";
  if (!results.length) verdict = "YELLOW";
  else if (results.some((r) => r.verdict === "RED")) verdict = "RED";
  else if (results.some((r) => r.verdict === "YELLOW")) verdict = "YELLOW";
  return {
    label: `audit ${dir}`,
    verdict,
    files: results,
    total_records: results.reduce((n, r) => n + r.records, 0),
    total_chained: results.reduce((n, r) => n + r.chained, 0),
    total_forks: results.reduce((n, r) => n + r.forks, 0),
  };
}

export function renderAudit(state) {
  const mark = { GREEN: "OK ", YELLOW: "?? ", RED: "XX " };
  const forkNote = state.total_forks ? `, ${state.total_forks} fork(s)` : "";
  const lines = [
    `showwork-audit (js)  =>  ${state.verdict}  ` +
      `(${state.total_chained}/${state.total_records} records chained${forkNote})`,
  ];
  if (!state.files.length) lines.push("  no ledger files found");
  for (const r of state.files) {
    const head = r.head ? `  head ${r.head.slice(0, 16)}` : "";
    const forked = r.forks ? `  (${r.forks} fork, ${r.heads.length} heads)` : "";
    lines.push(`  ${mark[r.verdict]} ${r.file}${head}${forked}`);
    lines.push(`       ${r.detail}`);
  }
  return lines.join("\n");
}

const EXIT_BY_VERDICT = { GREEN: 0, YELLOW: 3, RED: 2 };

// CLI: node index.mjs [root] [--strict]
if (import.meta.url === `file://${process.argv[1]}` ||
    import.meta.url === new URL(`file:///${process.argv[1].replace(/\\/g, "/")}`).href) {
  const argv = process.argv.slice(2);
  const strict = argv.includes("--strict");
  const root = argv.find((a) => !a.startsWith("--")) || ".";
  const state = auditRoot(root, strict);
  console.log(renderAudit(state));
  process.exit(EXIT_BY_VERDICT[state.verdict]);
}
