# Gating CI on receipts

The `showwork verify` GitHub Action turns receipts from artifacts into
enforced contracts: a job fails when the ledger's integrity chain is broken,
when a session's claims do not verify, or when the session was closed with a
`--no-verify` bypass (the bypass is stamped on the record; CI reads it).

## Usage

```yaml
jobs:
  receipts:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: bmdhodl/showwork/actions/verify@main
        with:
          session: my-agent-session     # omit to audit the chain only
```

The action installs showwork from its own ref — no PyPI dependency, and the
verifier version always matches the action version you pinned.

## Inputs

| input | default | meaning |
|---|---|---|
| `root` | `.` | project root containing `.showwork/` |
| `session` | *(empty)* | session id to verify; empty audits the chain only |
| `strict` | `false` | fail on YELLOW too (unprovable/partially verified) |
| `allow-commands` | `false` | execute locked `command` checks |

## What fails the job

- **Chain break** (`showwork audit` RED): history was tampered with, a
  record was deleted, or something appended outside the writer.
- **Failed claim** (`showwork verify --session` RED): a claimed "done" is
  not backed by the checked-out reality.
- **No exit-gate close**: the session has no `session.finish` event — the
  agent never went through the gate.
- **Bypass stamp**: the session closed with `--no-verify`. A bypassed gate
  is not a clean close, and the record says so durably.
- With `strict: true`, YELLOW also fails: pre-chain-only ledgers,
  checker errors, failed YELLOW-severity claims.

## Fork-PR safety

`command` checks execute a (locked) `python <script under project root>` —
that is repo code, and running repo code from an untrusted fork inside a
privileged workflow is how CI gets owned. By default the action sets
`SHOWWORK_NO_COMMANDS=1`: command checks refuse to run and report an error,
the verdict honestly degrades to YELLOW ("partially verified"), and the
default non-strict gate still passes on everything else. Enable
`allow-commands: true` only for same-repo branches you trust, e.g.:

```yaml
        with:
          session: my-agent-session
          allow-commands: ${{ github.event.pull_request.head.repo.full_name == github.repository }}
```

## Mapping sessions to PRs

The simplest convention: one agent session per branch, session id = branch
name (or task slug), recorded in the PR body by the agent. Receipts commit
with the work, so `verify --session` runs against exactly the ledger state
the PR proposes. A missing-receipt policy for human contributors is a repo
decision: run the audit-only form (no `session` input) on every PR and the
session-verifying form on agent-labeled PRs.

## The step summary is the receipt

Both the audit and the session verification render into the job's step
summary — reviewers see the OK/XX table and per-file head hashes without
leaving the PR. Publishing a head hash anywhere out-of-band anchors the
entire ledger history behind it.
