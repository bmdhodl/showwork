# Shared-test negative control, October 8, 2026

Base: `9835b5415ae241cf1c89744331f50e93536619f6`. Local branch:
`codex/negative-control-20261008`. Requested follow-up to the private showwork
research packet. No publication or remote write is part of this work.

The first proposal extends the existing [acceptance-review recipe](../acceptance-review.md)
and closed issue #95 rather than replace their working persistence example.
The initial packet did not identify that existing implementation. This change
adds only the missing reusable comparison: one shared unittest suite, a supplied
broken implementation and its repair, separate scratch directories, and an
inspectable result. Test protection and sandboxing remain separate proposals.

## Observed checks

Before the runner existed, its tests produced 11 failures and one passing
CLI-negative check. The first attempt could not create pytest's temp directory;
creating its missing parent fixed that setup error before the real failing run.
The CLI-negative test was later strengthened to require the intended diagnostic,
so a missing script no longer satisfies that check.

A further regression exposed unittest's classification of assertion failures
in fixture setup: the comparison returned an ordinary failure, not inconclusive.
The repaired runner treats assertions outside the test method as setup/teardown
errors. The regression now makes setup fail only against the broken source,
which would otherwise look like sensitivity to a production defect.

The focused runner and existing acceptance example passed 27 tests. They cover
real fail/repair behavior, vacuous tests, import/syntax/runtime and setup errors,
empty/skipped/expected-failure suites, changed test inventories, a still-broken
repair, invalid limits, timeout cleanup, input preservation and output paths.

The [retained comparison](../../.showwork/artifacts/codex-negative-control-20261008/comparison.json)
records the bundled persistence example: the empty save fails, the repaired save
passes the same test including a fresh-process read. The test supplies only a
new empty directory and the value to save. Input and output hashes describe
these authored fixtures, not external customer evidence.

The [full-suite log](../../.showwork/artifacts/codex-negative-control-20261008/full-suite.txt)
holds the actual repository test result. The session receipt records the
acceptance rerun at finish; the tracked gate is checked after the local commit.
No GitHub CI job is triggered because the owner prohibited external publication.

The read-only history audit reports YELLOW for existing pre-chain history.
The selected session must still have a sound chain and pass its own outcome
checks. No historical ledger is rewritten or excused by a new baseline here.

## Scope and review

The result says `SENSITIVE`, `INSENSITIVE`, `REPAIR_FAILED` or `INCONCLUSIVE`.
It does not claim application completion or automatic test adequacy. Reports
explicitly leave independent review unestablished. This work used self-review
and authored tests; no independent human adequacy review or customer trial ran.

This is a source-checkout example with stdlib unittest, not a new core command,
ledger schema, dependency, mandatory gate or arbitrary test-runner protocol.
Test code runs with the caller's privileges and can forge observations or use
paths outside scratch. Isolating input copies protects the normal workflow
from in-place edits; it is not a security boundary. A failure unrelated to the
declared defect can still produce a sensitivity signal. A reviewer must assess
the fixture, assertion and production path.

The original main checkout and its unrelated work were preserved. Work lives
in `E:/C-Offload/github/showwork-negative-control-20261008` for local review.

Receipt: `codex-negative-control-20261008`.
Sign-off: OpenAI | GPT-6 | auto.
