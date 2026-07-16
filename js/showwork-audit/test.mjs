/**
 * Conformance: the JS auditor must produce the same verdicts as the Python
 * reference implementation on the shared fixtures. expected.json is the
 * contract; tests/fixtures/chain/ holds the frozen bytes.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import * as fsExtra from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { auditFile } from "./index.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const fixtures = join(here, "..", "..", "tests", "fixtures", "chain");
const expected = JSON.parse(readFileSync(join(fixtures, "expected.json"), "utf8"));

for (const [name, want] of Object.entries(expected)) {
  test(`fixture ${name}`, () => {
    const got = auditFile(join(fixtures, name));
    assert.equal(got.verdict, want.verdict, `${name}: verdict`);
    assert.equal(got.break_at, want.break_at, `${name}: break_at`);
    if (want.chained !== undefined) assert.equal(got.chained, want.chained);
    if (want.pre_chain !== undefined) assert.equal(got.pre_chain, want.pre_chain);
  });
}

test("tampering one byte of an intact ledger flips it RED", () => {
  const { mkdtempSync, writeFileSync } = fsExtra;
  const dir = mkdtempSync(join(tmpdir(), "swjs-"));
  const path = join(dir, "intact.jsonl"); // same name => same genesis anchor
  const tampered = readFileSync(join(fixtures, "intact.jsonl"), "utf8")
    .replace('"one"', '"0ne"');
  writeFileSync(path, tampered, "utf8");
  const got = auditFile(path);
  assert.equal(got.verdict, "RED");
  assert.equal(got.break_at, 2);
});
