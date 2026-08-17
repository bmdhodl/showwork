# showwork integrity-command-replay design readout

Date: 2026-08-16
Scope: evidence-only. No verifier, receipt schema, workflow, runner, public
copy, release, or production change was made.

## Blocking finding

PR #30 is still held because the earlier 2-row matrix was too narrow. It
proved only a small session artifact and did not preserve the disposable-corpus
matrix, the historical timing readout, or the raw-record history needed for a
truthful closure.

This report now preserves:

- the local-only owner snapshot at `45d2420`
- the reviewed replay receipt head at
  `3b095d2bbc179ee6fb5a5e63bfdae245932111e7`
- the pre-follow-up merged-main snapshot at
  `2c6655cb684a73084dd32cd0a3ebbfe243ef13fd`
- the disposable semantic/refusal matrix

Older local snapshots from other checkouts are kept separate from the exact
working-tree truth and are not treated as current for this lane.

## Raw-record comparison

The raw-record method is explicit: iterate every `.showwork/claims-*.jsonl`
file in the named commit, count records whose `check.type` is `command`, and
separately count exact `argv == ["python", "scripts/run_tests.py"]`.

```powershell
@'
import json
import subprocess

commits = [
    "3b095d2bbc179ee6fb5a5e63bfdae245932111e7",
    "2c6655cb684a73084dd32cd0a3ebbfe243ef13fd",
]

for commit in commits:
    files = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", commit, ".showwork"],
        text=True,
    ).splitlines()
    claim_files = [
        path for path in files
        if path.startswith(".showwork/claims-") and path.endswith(".jsonl")
    ]
    total = 0
    run_tests = 0
    for path in claim_files:
        raw = subprocess.check_output(["git", "show", f"{commit}:{path}"], text=True)
        for line in raw.splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            if obj.get("check", {}).get("type") == "command":
                total += 1
                if obj["check"].get("argv") == ["python", "scripts/run_tests.py"]:
                    run_tests += 1
    print(commit, total, run_tests)
'@ | python -
```

Results:

- `3b095d2bbc179ee6fb5a5e63bfdae245932111e7` is the reviewed replay receipt
  head. The same raw-record method on that exact SHA yields
  `145` command records and `134` exact
  `["python", "scripts/run_tests.py"]` claims.
- `2c6655cb684a73084dd32cd0a3ebbfe243ef13fd` is the pre-follow-up merged main
  snapshot. The same
  raw-record method on that exact SHA also yields
  `145` command records and `134` exact
  `["python", "scripts/run_tests.py"]` claims.
- `PR63 reviewed-head ledger` is the live working-tree ledger after the
  append-only receipt rows in this follow-up. The same raw-record method over
  the PR working tree now yields `150` command records and `134` exact
  `["python", "scripts/run_tests.py"]` claims.

The local-only `45d2420` snapshot is preserved here only as a historical
observation. It reproduces `96` command records and `92` exact
`["python", "scripts/run_tests.py"]` claims, but it is not reproducible from
origin/main and is not part of the runnable snippet above. Normal reviewers
cannot derive it from the current working-tree truth.

## PR63 reviewed-head ledger recompute

The PR63 reviewed-head ledger recompute is pinned to the immutable reviewed
commit, not the live working tree. The exact raw-record method names that SHA
explicitly:

```powershell
@'
import json
import subprocess

reviewed_commit = "c60f554dd3c46b7b06c5713c445dee996c771aa7"
total = 0
run_tests = 0
files = subprocess.check_output(
    ["git", "ls-tree", "-r", "--name-only", reviewed_commit, ".showwork"],
    text=True,
).splitlines()
for path in sorted(
    p for p in files if p.startswith(".showwork/claims-") and p.endswith(".jsonl")
):
    raw = subprocess.check_output(["git", "show", f"{reviewed_commit}:{path}"], text=True)
    for line in raw.splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        if obj.get('check', {}).get('type') == 'command':
            total += 1
            if obj['check'].get('argv') == ['python', 'scripts/run_tests.py']:
                run_tests += 1
print(reviewed_commit, total, run_tests)
'@ | python -
```

That immutable reviewed head returns `150` command records and `134` exact
`["python", "scripts/run_tests.py"]` claims.

## Replay receipt head and narrow audit artifact

The exact replay receipt head is
`3b095d2bbc179ee6fb5a5e63bfdae245932111e7`.

The exact-head GitHub Codex review comment is `5310119545`, and the
independent exact-head QA verdict was CLEAN.

The dedicated audit-session artifact at
`.showwork/audit-session-integrity-command-replay-design-20260816.md` is
intentionally narrow and currently reads GREEN 2/2:

- command checker preserves the `SHOWWORK_NO_COMMANDS` refusal boundary
- full test suite passes for the replay readout

That artifact is supporting evidence, not a substitute for the raw-record
comparison above.

## Terminal receipts and merge-main verification

The replay lane's exact merged-main receipts are:

- PR checks: `8/8 GREEN` after infra-only reruns
- Merge commit: `2c6655cb684a73084dd32cd0a3ebbfe243ef13fd`
- Merge-main CI run: `31979022686 GREEN`
  - `test` job `95242774670`
  - `conformance-js` job `95242774717`
  - `receipts` job `95242774747`
- Reviewed blobs are identical on origin/main

The exact base/head strict-audit comparison recorded earlier was:

- Detached base `43545d0f26f030a3f32af5f3fc28a6854416455e`
- Replay head `3b095d2bbc179ee6fb5a5e63bfdae245932111e7`
- Result on both: `RED (369/401 records chained, 4 fork(s))`
- Fork identities remained the same on both sides

## Timing evidence

The observed hosted strict step from job `95115458538` ran from
`04:33:47Z` to `04:38:39Z`.

The earlier `18–20m` figure was a local-runtime multiplication estimate, not
an observed hosted duration. It is superseded by the observed hosted strict
step window above.

The preserved local timing fixture from the fixture run against source commit
`5552954` remains separate and was reported as:

```json
{
  "synthetic_claims": 96,
  "command_execution_96_seconds": 6.280858,
  "command_execution_result_counts": {"('pass', 'exit 0')": 96},
  "evaluate_records_command_96_seconds": 5.810864,
  "evaluate_records_command_state": {"verdict": "GREEN", "passed": 96, "total": 96},
  "evaluate_records_file_96_seconds": 0.014913,
  "evaluate_records_file_state": {"verdict": "GREEN", "passed": 96, "total": 96},
  "receipt_write_96_bytes": 11990,
  "receipt_write_96_seconds": 0.000421
}
```

## Deterministic disposable-corpus reproducer

The current PR63 clean worktree was rerun with the following self-contained
command. It uses a disposable temp root, the public `verify_claim` API, and a
tiny Python corpus to keep the evidence deterministic:

```powershell
$env:PYTHONPATH='src'
@'
from pathlib import Path
from tempfile import TemporaryDirectory
from showwork.checks import chk_command, verify_claim, NO_COMMANDS_ENV


def rec(check, claim='test claim', severity='RED'):
    return {'session': 'matrix', 'claim': claim, 'severity': severity, 'check': check}


with TemporaryDirectory() as td:
    root = Path(td)
    (root / 'stdout_a.py').write_text("print('A')\n", encoding='utf-8')
    (root / 'exit_zero.py').write_text('raise SystemExit(0)\n', encoding='utf-8')
    (root / 'counter.py').write_text(
        "from pathlib import Path\n"
        "p = Path('counter.txt')\n"
        "n = int(p.read_text()) if p.exists() else 0\n"
        "p.write_text(str(n + 1))\n"
        "print(n + 1)\n",
        encoding='utf-8',
    )

    checks = [
        ('stdout_A', {'type': 'command', 'argv': ['python', 'stdout_a.py'], 'stdout_contains': 'A'}),
        ('stdout_B', {'type': 'command', 'argv': ['python', 'stdout_a.py'], 'stdout_contains': 'B'}),
        ('exit_0', {'type': 'command', 'argv': ['python', 'exit_zero.py'], 'expect_exit': 0}),
        ('exit_1', {'type': 'command', 'argv': ['python', 'exit_zero.py'], 'expect_exit': 1}),
        ('counter_1', {'type': 'command', 'argv': ['python', 'counter.py'], 'stdout_contains': '1'}),
        ('counter_2', {'type': 'command', 'argv': ['python', 'counter.py'], 'stdout_contains': '2'}),
    ]

    import os
    saved_no_commands = os.environ.pop(NO_COMMANDS_ENV, None)
    try:
        for name, check in checks:
            result = verify_claim(rec(check), root)
            print(name, result['status'], result['detail'])
        os.environ[NO_COMMANDS_ENV] = '1'
        status, detail = chk_command({'type': 'command', 'argv': ['python', 'counter.py']}, root)
        print('no_commands', status, detail, (root / 'counter.txt').read_text(encoding='utf-8'))
    finally:
        if saved_no_commands is None:
            os.environ.pop(NO_COMMANDS_ENV, None)
        else:
            os.environ[NO_COMMANDS_ENV] = saved_no_commands
'@ | python -
```

Current rerun result:

- `stdout_A` → `pass`, `exit 0, stdout has 'A'`
- `stdout_B` → `fail`, `stdout missing 'B'`
- `exit_0` → `pass`, `exit 0`
- `exit_1` → `fail`, `exit 0, expected 1`
- `counter_1` → `pass`, `exit 0, stdout has '1'`
- `counter_2` → `pass`, `exit 0, stdout has '2'`
- `no_commands` → `error`, `command checks disabled by SHOWWORK_NO_COMMANDS (policy: do not execute repo code in this context)`, counter remained `2`

The replay snippet is self-contained: it clears any inherited `SHOWWORK_NO_COMMANDS` value before the normal/predicate/counter rows, sets it only for the refusal row, and restores the original inherited value afterward.
Before the row loop, it saves inherited SHOWWORK_NO_COMMANDS, clears it up front, and restores it afterward even when pre-exported.

This is the evidence the earlier 2-row artifact was missing. It proves the
same argv can produce different outcomes under different predicates, state, and
policy, so argv is not a safe cache key.

## Semantic and refusal matrix

The disposable matrix for this lane is the deterministic one above, not the
two-row session artifact. It covers:

- same argv with different stdout predicates (`A` vs `B`)
- same argv with different expected exits (`0` vs `1`)
- repeated same argv with counter side effects (`1` then `2`)
- `SHOWWORK_NO_COMMANDS=1` refusal with the counter unchanged

That matrix is intentionally minimal but complete for the claim the card makes.

## Evidence mapping

This lane ties each review-thread dimension to a concrete receipt:

- Identity: replay receipt head `3b095d2bbc179ee6fb5a5e63bfdae245932111e7`,
  pre-follow-up merged-main snapshot `2c6655cb684a73084dd32cd0a3ebbfe243ef13fd`,
  exact-head review comment `5310119545`, and the live PR63 reviewed-head
  ledger row.
- Order/state: the raw-record counts above, the merged-main CI run
  `31979022686`, and the observed hosted strict step window
  `04:33:47Z-04:38:39Z`.
- Environment/policy: the disposable matrix row that returns `error` under
  `SHOWWORK_NO_COMMANDS=1`, plus the narrow audit artifact that records the same
  refusal boundary.
- Path/cwd: the raw-record snippet walks exact Git SHAs via `git show` and the
  deterministic temp-root matrix uses an isolated `TemporaryDirectory()`.
- Refusal: the `no_commands` row, the dedicated audit-session artifact, and the
  strict-audit comparison that remains `RED (369/401 records chained, 4 fork(s))`
  on both base and head.
- Tamper: actual tampered-receipt verification is PR #62 job `95242167332` /
  run `31977845414` SUCCESS (`2026-08-16T23:12:52Z-23:14:43Z`); the same-argv
  rows stay under identity/expectation/state.
- Append-only: the `.showwork/claims-2026-08-16.jsonl` retractions and
  replacement claims preserve history instead of rewriting it, and the matching
  `.showwork/sessions.jsonl` finish/refused transitions preserve session order.

## Why equal argv is not a safe cache key

The same `python scripts/run_tests.py` argv text appears many times across the
ledger, but it is not equivalent to claim identity. The raw-record totals above
show why: identical argv text exists in both the historical owner-only snapshot
and the pre-follow-up merged-main snapshot, and now also in the live PR63
reviewed-head ledger, yet the surrounding claim context, timing, and ledger
history differ. Any optimization must preserve claim order, refusal semantics,
tamper behavior, and append-only history, not just argv equality.

## Validation summary

The current exact-main worktree was revalidated with:

- `python -m pytest tests/test_checks.py -q` → `76 passed in 10.21s`
- `python -m pytest tests/ -q` → `274 passed`
- `python -m ruff check .` → `All checks passed!`
- `python -m showwork.cli verify --no-report --date 2026-08-16` → `GREEN (49/112 verified)`
- `python -m showwork.cli audit --strict` → `RED (369/401 records chained, 4 fork(s))`

The strict audit is intentionally still red on the replay receipt history and
the live PR63 working tree, with the same four historical fork identities
preserved. This is consistent with the earlier base/head comparison above and
with the pre-follow-up merged-main raw-record counts.

## Boundaries

This report does not change source code, workflow files, schema, or release
controls. It records the evidence mismatch that keeps PR #30 held until the
source evidence PR is merged and the Vault closure report is amended to match
the exact follow-up truth.
