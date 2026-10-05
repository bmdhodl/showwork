# Receipts in pull requests

Receipt verification and merge policy are separate choices. Showwork always
reports the actual verification result. A repository decides whether an
unverified receipt should block merging.

## Repository test lanes

Every PR, including forks, runs behavioral/conformance tests, receipt UI checks,
the JavaScript auditor and the ten clean-room action cases on disposable hosted
runners with read-only permissions and no persisted checkout credentials. The
receipt-command review job remains limited to trusted branches and advisory.
Its successful job status must not be described as a verified outcome.

Nightly at 08:37 UTC, package compatibility builds and installs the current
commit's wheel. The installed CLI must refuse a missing artifact and accept it
after creation, then pass the other release-smoke cases. Behavioral tests run
on Linux Python 3.10 through 3.13, Windows 3.13 and macOS 3.13. Manual dispatch
is available. Each matrix job has a 20-minute bound and records its exact commit
and dependency versions. This workflow does not publish or sign a release.

A separate five-minute nightly job runs `showwork audit --json` across every
historical ledger file and retains the full result as a 14-day Actions artifact.
It preserves the CLI's exit code: legacy unchained records produce YELLOW (3),
tampering produces RED (2), and only GREEN returns zero. Existing historical
debt is not rewritten, allowlisted or converted into passing integrity. Package
matrix results remain independent of this job's conclusion.

This is a chain-integrity audit, not replay of historical claim checks. It reads
ledger bytes without executing recorded commands or HTTP probes. A non-green
audit artifact describes integrity findings; it does not prove the current
package's behavioral tests failed.

The separate historical-replay job evaluates every loaded claim and acceptance
requirement against the current checkout with `scripts/replay_history.py`.
Retractions withdraw claims but cannot erase acceptance requirements. Duplicate
or malformed requirements fail. Missing check specs remain unverified (YELLOW),
and stale historical assertions retain their actual RED/YELLOW results. The
complete JSON result is retained for 14 days. This does not reconstruct old
environments or certify past session outcomes, and does not replace the audit.
Claims and requirements are loaded before execution; a final byte-level ledger
comparison fails if any command changed or removed historical records.

Replay may share raw output from the normalized Python invocation of
`scripts/run_tests.py` within that single replay. Accepted `python3` and virtual
environment interpreter aliases normalize to the same actual executable and
share that execution too. Every assertion still checks its own expected exit
code and output text. Reuse requires the same bounded source snapshot, resolved
command, environment and timeout. Executing another script clears that reuse;
source changes during execution fail and clear it too. Results identify the
execution and whether it was reused, with output hashes rather than raw output.
There is no persistent cache, and ordinary CLI verification does not opt in.
The source snapshot excludes generated/dependency trees and large files; this
is intended for the isolated repository CI checkout with fixed dependencies,
not arbitrary live environments. The job has a 30-minute bound and uses the
existing 600-second per-command allowance. Real nightly observation remains
required before rollout acceptance.

The hourly integration candidate (`integration.yml`, minute 19 UTC) checks out
the immutable event SHA on standard hosted Ubuntu. It builds and installs that
commit's wheel, exercises the installed CLI, then runs outcome and CLI cases.
Admission reads Actions history for the same commit, which also fixes suite,
lockfile and workflow identity. It reuses only an actual successful `integration`
job from the last 24 hours. Nightly OS/Python compatibility still runs regardless
of source changes; hourly admission does not replace it.

A newer failed execution invalidates an older pass. One automatic retry is
allowed; two failed or timed-out executions defer additional work at that SHA.
Actual integration-job completion orders passes, failures and recoveries. A late
reporter cannot make an older pass hide a newer failure, or erase a later recovery.
The selector reads job evidence for the bounded history window before ordering it;
workflow update timestamps are not execution evidence. Timezone-free and future
job completion timestamps are refused.

An explicit manual `force` dispatch may retry after triage, but cannot override
an observed active equivalent run. Incomplete/unavailable
history refuses selection rather than resetting that budget. An active equivalent
run defers the tick, and the hourly concurrency group keeps the latest pending
tick without cancelling an executing probe. PR, nightly and release groups remain
separate.

Read coverage freshness from the last successful **integration job**, not the
workflow's aggregate conclusion: admission-only workflows may succeed while
integration is skipped. The admission summary reports `already-verified`,
`deferred-active` or `deferred-retry-limit`, with the existing evidence run ID.
Skipped ticks do not update the tested timestamp. This candidate still needs
failure-to-incident routing and hosted dispatch/skip/retry verification before
activation is accepted. Local selector tests are not scheduled-execution proof.

The behavioral suite runs through the existing genesis receipt once, using
`python scripts/check_ci_genesis.py`. The entry point refuses a missing,
retracted, duplicated or changed suite command before execution. It uses the
normal verifier for both the full test command and the remaining genesis
artifact claims. It does not cache results, rewrite receipts or omit tests.
The genesis step explicitly allows 600 seconds for its command inside the
15-minute job. Without this setting the verifier's 120-second default can
terminate a passing full suite. This is a bounded execution budget, not a
timeout retry or a waiver; a suite exceeding it still fails.
Real subprocess fixtures prove one execution and propagation of suite failures,
missing success output and missing artifacts. This removes only the standalone
invocation that immediately repeated the same suite on the same checkout.

Today's claims still run separately, as do the trusted changed-receipt checks.
They may replay commands again; further deduplication remains pending. Neither
date-scoped verification nor the genesis receipt replays every historical
session, and neither is a hash-chain audit (`showwork audit`). The separate
nightly replay and integrity jobs provide those checks with distinct results.

## Choose a policy

- **Advisory:** run the checks, show failures in the job summary, and warn on an
  unverified receipt without blocking the PR. Ordinary tests still gate the work.
- **Enforce:** fail the job when the receipt is unverified. Use this for workflows
  that require a complete outcome receipt, such as release approval.

The action defaults to `mode: enforce` for compatibility. This repository's
receipt job explicitly uses `mode: advisory`. `finish` and the CLI `gate` remain
strict in either case. Advisory mode does not create or repair a receipt and
never converts an UNVERIFIED outcome to VERIFIED.

**Availability:** `mode` and the action outputs below ship in v0.6.5.
Workflows pinned to `v0.6.4` or earlier do not gain these options.

## Checkout matters

Use `fetch-depth: 0` and check out `github.event.pull_request.head.sha` for the
receipt job. A receipt describes the branch's work. GitHub's default synthetic
merge checkout can include unrelated main-branch edits and make those edits look
like undeclared changes. Keep ordinary build and test jobs on the merge checkout
if you want to test integration with main.

Pass `github.event.pull_request.base.sha` as `changed-since`. Current source
selects receipts from that revision's **merge base with HEAD**, matching a PR's
Files changed view. Receipts added only on main are excluded. Receipts deleted
or moved by the PR still get checked. No changed receipts remains UNVERIFIED.

The same revision is the trusted base. When a branch merges main after its
session started, a file that main changed differs from the start snapshot.
showwork 0.6.6 excuses that file only when it now equals the base revision
exactly, and lists it as a note. An edit by the session or inside the merge
still fails. Take the base from the event, never from a ref the branch can move.

```yaml
jobs:
  receipts:
    if: github.event.pull_request.head.repo.full_name == github.repository
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683
        with:
          fetch-depth: 0
          ref: ${{ github.event.pull_request.head.sha }}
      # Install your acceptance commands' dependencies before this step.
      # Pin uses: to a reviewed showwork commit that includes advisory mode.
      - uses: ./actions/verify  # works inside a checkout of showwork itself
        id: receipts
        with:
          mode: advisory
          changed-since: ${{ github.event.pull_request.base.sha }}
          allow-commands: "true"
          require-tracked: "true"
```

For another repository use `bmdhodl/showwork/actions/verify@<reviewed-commit>`.
The full SHA behind `v0.6.5` is `0502f87ed38faaea0a09c01a795d7d5ae15aa91d`.
Do not run `@main` in a gate you trust. The action installs its own pinned source,
not the latest PyPI package. Upgrade deliberately; no release is required when
pinning a reviewed commit.

## Inputs and outputs

| Input | Default | Meaning |
| --- | --- | --- |
| `mode` | `enforce` | `advisory` reports refusal without failing the job |
| `root` | `.` | Project root containing `.showwork/` |
| `session` | empty | One session; mutually exclusive with `changed-since` |
| `changed-since` | empty | Select receipts changed from the merge base with this revision; files that equal it are not undeclared changes |
| `require-tracked` | `true` | Receipt files must match committed HEAD |
| `python-path` | empty | Prepared interpreter with test dependencies; otherwise an isolated venv |
| `allow-commands` | `false` | Execute repository Python checks in a trusted context |
| `allow-network` | `false` | Permit HTTP checks in a trusted context |
| `legacy-integrity-baseline` | empty | Reviewed immutable commit acknowledging unchanged shared legacy files |
| `strict` | `true` | Deprecated; does not weaken the verifier |

Supply exactly one of `session` and `changed-since`. The action exposes `result`
(`verified`, `unverified`, or `error`) and the original `exit-code`. A successful
advisory job is not evidence that the receipt passed: inspect `result` and the
summary. Installation failures, invalid mode/selection, and unexpected verifier
exit codes still fail the job. A gate refusal (exit 2), including a missing
receipt or unresolved revision, is reported as unverified in advisory mode.

From v0.6.6 the summary shows one section per selected session in the existing
check summary. Each section names the declared requirement, its scope and observed
result, and links to the committed session receipt at the reviewed HEAD. Command
rows show their observed revision, exit code and stdout hash. A disabled command
has no executed test evidence; an empty receipt has no declared acceptance.
Rerunning at another SHA produces a new summary for that HEAD. Historical integrity
and missing definitions remain visible even when advisory policy lets the job pass.

The summary formats the gate result already obtained; it does not execute checks
again. It never assesses test adequacy or fills undeclared requirements. Display
limits are explicit, and the verifier still uses every selected row. These summary
improvements need the action pinned to v0.6.6 or a later reviewed commit.
Actions pinned to v0.6.5 or earlier keep the original text summary.

Command and network checks remain disabled unless explicitly enabled. Disabled
checks do not certify behavior. Never enable repository commands in a privileged
workflow running untrusted fork code. The example skips forks; use a separate
isolated test workflow for them.

## Existing installations

The [drop-in workflow](ci/verify.yml) and `showwork init --ci` template use the
reviewed commit containing the merge-base selector. They select the PR head with full history.
For workflows still pinned to v0.6.4 or earlier, to stop that
older action from blocking while retaining its visible failure, set
`continue-on-error: true` on the **receipt action step** and inspect its
`steps.<id>.outcome` in a following warning step. Do not apply it to the build or
test jobs. Unlike the new advisory mode, this older fallback also tolerates action
setup failures. Upgrade the pinned action to use the narrower advisory policy.

Changing this repository does not update consumer workflows or existing PRs.
Each consumer must update its action pin and policy. No branch protection
change is needed when the required receipt job itself uses advisory mode.

## Diagnose a refusal

- **Unrelated paths changed:** check out the PR head, not `refs/pull/*/merge`.
  A file main changed is excused only when it equals the base exactly; merge
  main again if the base moved after your last merge. If the branch itself was
  rebased after recording the snapshot, review the changed paths and record a
  new session against that tree; do not edit history.
- **Base already contains HEAD:** pass the branch the change merges into, not
  the branch itself. Locally: `showwork gate --session <slug> --base origin/main`.
- **Unrelated session selected:** upgrade to the merge-base selector above.
- **Cannot resolve a common receipt base:** fetch both revisions with full Git
  history. A shallow checkout cannot reliably identify the PR's changes.
- **No successful outcome close:** declare requirements before claims, run the
  checks, finish successfully, and commit the session, claims, and snapshot.
- **Command unavailable:** prepare test dependencies and pass `python-path` if
  they live in a job-specific Python environment.
- **Historical integrity RED:** review [legacy adoption](legacy-baseline.md).
  A baseline acknowledges immutable shared history; it never makes it GREEN.

See [evidence scope](evidence-scope.md) for what receipts can and cannot prove.
Checks cannot establish whether the requirements fully cover the user's request.

## Platform regression follow-up

The hourly integration lane reports admission or execution failures in one
marked GitHub issue. Repeated failures of the same kind at the same commit do
not add notifications. New failed commits update that issue with their execution
link. Only an actual successful integration on the default branch closes it;
skipped, cancelled and non-default-branch runs cannot claim recovery. API errors
fail the reporting job loudly. The issue is the repair handoff: reproduce once,
classify code versus infrastructure/configuration, and use reviewed changes.
After the retry limit, a triaged manual force can resume execution. This uses
existing Actions history and GitHub issues, with no mutable local CI state file.
An issue-reporting failure does not invalidate a successful integration job or
cause its tests to rerun hourly. That reporting failure remains visible in its
job result. Reusing a prior pass does not claim a new run or close an incident;
recovery still requires actual integration execution (or a triaged manual force).

The supported Python 3.10 lane uses the `tomli` backport only for tests that read
`pyproject.toml`. Python 3.11 and newer use standard-library `tomllib`. Local full
suite setup on Python 3.10 needs
`python -m pip install build pytest "setuptools>=77.0.3" wheel tomli`.
The installed-package test's offline build uses the declared setuptools floor;
an older setuptools bundled in a Python 3.10 venv cannot build this project.
The shipped package still has no runtime dependencies. The first scheduled-matrix
dispatch exposed the missing test import; do not skip packaging or handoff tests
to make that lane pass.

The Windows and macOS lanes also exposed receipt-manifest failures when a temp
directory has an alias (Windows short names or macOS `/var`). Manifest paths now
use the same resolved root as ledger paths. A regression exercises equivalent
root spellings without changing receipt bytes or weakening containment checks.
