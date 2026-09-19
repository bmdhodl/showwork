# SW-02 benchmark readout

Dated comparison for [issue #87](https://github.com/bmdhodl/showwork/issues/87).
This is a measurement, not a release. No PyPI tag is authorized.

Machine-readable snapshot: [results.json](results.json).
Fixture: [examples/sw-02-bench](../../../examples/sw-02-bench).

Recorded at 2026-09-19T04:49:19Z on Windows 11, Python 3.13.2, pytest 8.4.2,
showwork 0.6.3, Node v22.14.0. Agent Verify 1.2.0 at commit
`b0212fd5c863f620e013f821d8234842adb8e8e3`. Local pytest is the CI analog.
No GitHub job ran this fixture.

## Setup and time

1. Copy `examples/sw-02-bench/seed` into a temp directory per case.
2. Run pytest on `test_add.py`.
3. Run showwork `start` / `require` / `claim` / `verify` or `finish`.
4. Optional: `node src/cli.mjs --message "All tests pass." --cwd <case>`.

Temp setup was 2 ms. Pytest and showwork alone were 12 141 ms.
The committed run with Agent Verify was 87 966 ms. Case walls with Agent
Verify sat between 10 191 ms and 12 587 ms.

## Denominator

8 cases frozen. 8 ran. 8 matched the frozen pytest and showwork verdicts.

Pytest was green while showwork was red on 3 cases: undeclared-deletion,
stale-revision, missing-receipt.

## One measured advantage

**Undeclared deletion.** `bystander.txt` is deleted after `session.start`.
No claim names that path. pytest stays exit 0. Agent Verify with message
`All tests pass.` stays exit 0. showwork `finish --status ok` exits 2.

Keep the snapshot gate. Do not replace it with a test-only verifier.

Stale-revision is the same class of gap: pytest stays exit 0 after
`bystander.txt` changes; showwork `verify` exits 2 because the content
claim no longer matches. It is supporting evidence, not a second product
bet.

## Cases

| Case | pytest | showwork | Agent Verify 1.2.0 | Label |
| --- | ---: | ---: | ---: | --- |
| honest-pass | 0 | finish 0 | 0 | honest |
| honest-fail | 1 | finish 2 | 1 | honest |
| never-run-test | 1 if run | artifact finish 0; behavior finish 2 | 1 | artifact close is false-green |
| weak-fixture | 0 | finish 0 | 0 | human-reviewed |
| undeclared-deletion | 0 | finish 2 | 0 | measured advantage |
| stale-revision | 0 after edit | verify 0 then 2 | 0 | supporting |
| missing-receipt | 0 | finish 2 | 0 | no check-backed close |
| cross-client-handoff | n/a | verify 0; session names `codex` | 0 | portable JSONL |

never-run-test: a handwritten `pytest-last.json` lets an artifact-only
showwork close go green. A behavior `require` that runs pytest exits 2.
Agent Verify re-runs tests when the message claims they passed, so it
exits 1 here. That is not a showwork win.

weak-fixture: the test monkey-patches `add` so pytest, a showwork command
check, and Agent Verify all stay green. Production `add(2, 2)` prints `5`.
A deterministic receipt cannot detect that omission. Adequacy is
human-reviewed.

missing-receipt: pytest is green with no prior showwork session.
`finish --status ok` exits 2 (`no_check_backed_claims`). Agent Verify
exits 0 because tests pass; it writes `.verify/last-receipt.json` when
invoked. A missing Agent Verify receipt exists only if you never call it.

cross-client-handoff: showwork `start --agent codex` then `verify` in the
same process. The JSONL still names `codex`. This is file portability, not
a live Cursor-to-Codex session. Agent Verify writes a gitignored
`.verify/last-receipt.json`.

## Untested hosts

| Target | Status | Reason |
| --- | --- | --- |
| Agent Receipts 0.2.0 | untested | rustc and cargo are missing on this host |
| PatchCase | untested | one receipt competitor was in scope; that was Agent Receipts |
| GitHub Actions job | untested | local pytest is the CI analog |
| Claude Code Stop hook | untested | this run is not a Claude Code session |
| Cursor hooks | untested | this run is not a Cursor hook dispatch |
| Codex native hooks | untested | this run is not a Codex session |

From Agent Verify source at the commit above, `scripts/codex-notify.mjs`
exits 0 even when checks fail. The blocking CLI is
`node src/cli.mjs --message`. showwork's own Stop hook observes and does
not block. Those statements are source readings, not live hook runs.

## False-clean and inconclusive

False-clean if you only watch pytest: undeclared-deletion, stale-revision,
missing-receipt.

False-green if you accept artifact text as a test run: never-run-test
artifact close.

Inconclusive: Agent Receipts, PatchCase, GitHub Actions, and native
Claude / Cursor / Codex hooks.

## Decision

Keep showwork. The unique measured gap versus pytest and versus Agent
Verify's tests verifier is undeclared tree damage. Existing test-only
tools are enough for honest-pass, honest-fail, and a re-run of tests.
They are not enough for a bystander delete.

Do not add a ledger, memory service, dispatcher, or paid product from this
card. Do not publish to PyPI from this card.
