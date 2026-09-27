# Receipts in pull requests

Receipt verification and merge policy are separate choices. Showwork always
reports the actual verification result. A repository decides whether an
unverified receipt should block merging.

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
| `changed-since` | empty | Compare HEAD against the merge base with this revision |
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
  If the branch itself was rebased after recording the snapshot, review the
  changed paths and record a new session against that tree; do not edit history.
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
