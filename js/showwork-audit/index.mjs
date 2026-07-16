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
 * Audit one ledger file's hash chain.
 * @param {string} filePath
 * @returns {{file: string, records: number, chained: number, pre_chain: number,
 *            head: string|null, break_at: number|null, detail: string, verdict: string}}
 */
export function auditFile(filePath) {
  const fileName = basename(filePath);
  const out = {
    file: fileName,
    records: 0,
    chained: 0,
    pre_chain: 0,
    head: null,
    break_at: null,
    detail: "",
    verdict: "GREEN",
  };
  let text = readFileSync(filePath, "utf8");
  if (text.charCodeAt(0) === 0xfeff) text = text.slice(1); // BOM
  let prevLine = null;
  let chainStarted = false;
  let lineNo = 0;
  for (const raw of text.split(/\r?\n/)) {
    lineNo += 1;
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    out.records += 1;
    const expected = prevLine !== null ? lineHash(prevLine) : genesisHash(fileName);
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
      if (prev !== expected) {
        out.verdict = "RED";
        out.break_at = lineNo;
        out.detail = `chain break at line ${lineNo}: prev is ${String(prev).slice(0, 12)}..., ` +
          `expected ${expected.slice(0, 12)}...`;
        return out;
      }
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
    prevLine = line;
  }
  if (prevLine !== null) out.head = lineHash(prevLine);
  if (out.records === 0) {
    out.verdict = "YELLOW";
    out.detail = "empty ledger file: nothing to anchor";
  } else if (out.chained === 0) {
    out.verdict = "YELLOW";
    out.detail = `${out.records} record(s), none chained yet: ` +
      `integrity is unprovable until the first chained append`;
  } else {
    out.detail = `intact: ${out.chained} chained record(s)` +
      (out.pre_chain ? `, ${out.pre_chain} pre-chain record(s) anchored` : "");
  }
  return out;
}

/** Audit every ledger file under a project root's .showwork/ directory. */
export function auditRoot(root) {
  const dir = join(root, ".showwork");
  const files = [];
  if (existsSync(dir) && statSync(dir).isDirectory()) {
    for (const name of readdirSync(dir).sort()) {
      if (/^claims-.*\.jsonl$/.test(name)) files.push(join(dir, name));
    }
    const sessions = join(dir, "sessions.jsonl");
    if (existsSync(sessions)) files.push(sessions);
  }
  const results = files.map(auditFile);
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
  };
}

export function renderAudit(state) {
  const mark = { GREEN: "OK ", YELLOW: "?? ", RED: "XX " };
  const lines = [
    `showwork-audit (js)  =>  ${state.verdict}  ` +
      `(${state.total_chained}/${state.total_records} records chained)`,
  ];
  if (!state.files.length) lines.push("  no ledger files found");
  for (const r of state.files) {
    const head = r.head ? `  head ${r.head.slice(0, 16)}` : "";
    lines.push(`  ${mark[r.verdict]} ${r.file}${head}`);
    lines.push(`       ${r.detail}`);
  }
  return lines.join("\n");
}

const EXIT_BY_VERDICT = { GREEN: 0, YELLOW: 3, RED: 2 };

// CLI: node index.mjs [root]
if (import.meta.url === `file://${process.argv[1]}` ||
    import.meta.url === new URL(`file:///${process.argv[1].replace(/\\/g, "/")}`).href) {
  const state = auditRoot(process.argv[2] || ".");
  console.log(renderAudit(state));
  process.exit(EXIT_BY_VERDICT[state.verdict]);
}
