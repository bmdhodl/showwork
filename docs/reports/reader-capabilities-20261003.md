# Process-free receipt readers

Issue: [#96](https://github.com/bmdhodl/showwork/issues/96).
Base: `978b1fe`, before the CI review fixes. No new package release is included.

The Python receipt view launched Git during root discovery and Python workers
for file regexes. Its CLI and the handoff reader now use process-free local APIs.
Python and JavaScript inspectors expose matching integrity, manifest, historical
outcome, freshness, scope and unsupported-semantics labels. They never reexecute
commands, and current acceptance remains UNVERIFIED on a historical inspection.
The Python overlay separately retains supported filesystem observations through
the existing checker and labels their scope. Regex, command, Git and network
checks are disabled there. A verified overlay requires a matching successful
recorded outcome close as well as passing supported current checks.

[Reader capabilities](../readers.md) document supported fields and versions,
bounds, snapshot scope and limits. Per-session writers and existing persisted
records are unchanged. Hash-chain inspection reuses the existing auditors with
the same bounded bytes that were loaded, avoiding a second unbounded file read.
JavaScript does not implement the Python behavior checkers.

The initial regressions failed because receipt reads launched Git. Frozen fixtures
cover a successful close, reopen, missing manifest, changed claims, tampering,
legacy data, required future semantics and duplicate keys. Both languages reject
escaping paths and oversized input. Disabled observations retain the claim and
reason without claiming that file content was searched. Handoff tests now confirm
that its API starts no child and that a regex failure requires an active verifier.

Validation on Windows, Python 3.13.2: 45 focused tests and the final full suite
passed 663 tests in 521.68 seconds. JavaScript passed 26 checks, with no skips.
Chromium passed interactive badge details, empty-state and overflow checks at
375/768/1440, with no page errors. The screenshot was inspected.
[Raw full-suite output](reader-capabilities-20261003/full-suite.txt) and
[browser preview](reader-capabilities-20261003/badges.png) are retained.

The first full run exposed four prior handoff tests that relied on executing
regex workers while reading. The example now uses a supported existence check
for its artifact-only lane and reports regex observation as disabled; an explicit
active check still fails the corrupted note. This preserves the distinction
between observation, execution and approval rather than removing the failure
assertion.

Receipt session: `codex-readers-01a1000f`.
Sign-off: OpenAI | GPT-6 | auto.
