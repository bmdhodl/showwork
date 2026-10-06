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
import { auditFile, inspectSession } from "./index.mjs";
import * as childProcess from "node:child_process";
import * as https from "node:https";
import { syncBuiltinESMExports } from "node:module";

const here = dirname(fileURLToPath(import.meta.url));
const fixtures = join(here, "..", "..", "tests", "fixtures", "chain");
const expected = JSON.parse(readFileSync(join(fixtures, "expected.json"), "utf8"));

const readerFixtures = join(here, "..", "..", "tests", "fixtures", "readers");
const readerExpected = JSON.parse(readFileSync(join(readerFixtures, "expected.json"), "utf8"));
for (const [name, want] of Object.entries(readerExpected)) {
  test(`reader fixture ${name}`, () => {
    const got = inspectSession(join(readerFixtures, name), "fixture");
    for (const [key, value] of Object.entries(want)) assert.equal(got[key], value, `${name}: ${key}`);
  });
}

test("reader names the session that superseded a closed claim", () => {
  // Session "fixture" claimed notes/v1-*.md and closed. Session "later"
  // renamed the note and superseded the claim from its own claims file.
  const fixture = join(readerFixtures, "superseded");
  const got = inspectSession(fixture, "fixture");
  assert.equal(got.manifest, "matches");
  assert.equal(got.recorded_outcome, "VERIFIED");
  assert.deepEqual(got.supersessions, [{
    claim: "one plan note matches notes/v1-*.md", ts: "2026-10-05T00:00:02",
    by: "later", reason: "the v2 release renames the plan note",
  }]);
  const dir = fsExtra.mkdtempSync(join(tmpdir(), "swjs-superseded-"));
  fsExtra.cpSync(fixture, dir, { recursive: true });
  fsExtra.rmSync(join(dir, ".showwork", "claims", "later.jsonl"));
  const bare = inspectSession(dir, "fixture");
  assert.deepEqual(bare.supersessions, []);
  // History only: this reader never checks the claim again.
  assert.equal(bare.recorded_outcome, "VERIFIED");
});

test("reader never invokes child processes or network", () => {
  const processDefault = childProcess.default;
  const networkDefault = https.default;
  const saved = { spawn: processDefault.spawn, execFile: processDefault.execFile,
    spawnSync: processDefault.spawnSync, execFileSync: processDefault.execFileSync,
    request: networkDefault.request, get: networkDefault.get };
  const forbidden = () => { throw new Error("reader invoked external execution"); };
  let calls = 0;
  const reject = () => { calls++; forbidden(); };
  try {
    for (const key of ["spawn", "execFile", "spawnSync", "execFileSync"]) processDefault[key] = reject;
    networkDefault.request = networkDefault.get = reject;
    syncBuiltinESMExports();
    assert.equal(inspectSession(join(readerFixtures, "closed"), "fixture").recorded_outcome, "VERIFIED");
    assert.equal(calls, 0);
  } finally {
    for (const key of ["spawn", "execFile", "spawnSync", "execFileSync"]) processDefault[key] = saved[key];
    networkDefault.request = saved.request;
    networkDefault.get = saved.get;
    syncBuiltinESMExports();
  }
});

test("reader rejects workspace escape and oversized files", t => {
  const dir = fsExtra.mkdtempSync(join(tmpdir(), "swjs-reader-"));
  const workspace = join(dir, "workspace"), outside = join(dir, "outside");
  fsExtra.mkdirSync(workspace);
  fsExtra.mkdirSync(outside);
  try {
    fsExtra.symlinkSync(outside, join(workspace, ".showwork"), "junction");
  } catch (error) {
    if (["EPERM", "EACCES"].includes(error.code)) return t.skip("host does not permit links");
    throw error;
  }
  assert.equal(inspectSession(workspace, "fixture").integrity, "unknown");
  const largeRoot = join(dir, "large");
  fsExtra.mkdirSync(join(largeRoot, ".showwork", "sessions"), { recursive: true });
  fsExtra.writeFileSync(join(largeRoot, ".showwork", "sessions", "fixture.jsonl"), Buffer.alloc(4 * 1024 * 1024 + 1));
  assert.equal(inspectSession(largeRoot, "fixture").integrity, "unknown");
});

for (const [name, want] of Object.entries(expected)) {
  test(`fixture ${name}`, () => {
    const got = auditFile(join(fixtures, name));
    assert.equal(got.verdict, want.verdict, `${name}: verdict`);
    assert.equal(got.break_at, want.break_at, `${name}: break_at`);
    if (want.chained !== undefined) assert.equal(got.chained, want.chained);
    if (want.pre_chain !== undefined) assert.equal(got.pre_chain, want.pre_chain);
    if (want.forks !== undefined) assert.equal(got.forks, want.forks);
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
