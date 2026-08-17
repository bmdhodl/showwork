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
- the current merged-main truth at
  `2c6655cb684a73084dd32cd0a3ebbfe243ef13fd`
- the disposable semantic/refusal matrix

A separate `95/91` local snapshot from another checkout exists in the wider
history, but this report does not treat it as current-main truth because it is
not bound to the exact named merged-main SHA above.

## Raw-record comparison

The raw-record method is explicit: iterate every `.showwork/claims-*.jsonl`
file in the named commit, count records whose `check.type` is `command`, and
separately count exact `argv == ["python", "scripts/run_tests.py"]`.

```powershell
@'
import json
import subprocess

commits = [
    "45d2420",
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

- `45d2420` is the local-only owner snapshot. It reproduces
  `96` command records and `92` exact
  `["python", "scripts/run_tests.py"]` claims.
- `3b095d2bbc179ee6fb5a5e63bfdae245932111e7` is the reviewed replay receipt
  head. The same raw-record method on that exact SHA yields
  `145` command records and `134` exact
  `["python", "scripts/run_tests.py"]` claims.
- `2c6655cb684a73084dd32cd0a3ebbfe243ef13fd` is current merged main. The same
  raw-record method on that exact SHA also yields
  `145` command records and `134` exact
  `["python", "scripts/run_tests.py"]` claims.

The important correction is that the local-only `45d2420` snapshot is not the
same thing as the merged-main ledger. This report therefore does not treat any
other checkout-local `95/91` count as current main truth.

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

The preserved local timing fixture from the historical `5552954` receipt
branch remains separate and was reported as:

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

    for name, check in checks:
        result = verify_claim(rec(check), root)
        print(name, result['status'], result['detail'])

    import os
    os.environ[NO_COMMANDS_ENV] = '1'
    status, detail = chk_command({'type': 'command', 'argv': ['python', 'counter.py']}, root)
    os.environ.pop(NO_COMMANDS_ENV, None)
    print('no_commands', status, detail, (root / 'counter.txt').read_text(encoding='utf-8'))
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

## Why equal argv is not a safe cache key

The same `python scripts/run_tests.py` argv text appears many times across the
ledger, but it is not equivalent to claim identity. The raw-record totals above
show why: identical argv text exists in both the historical owner-only snapshot
and the current merged main, yet the surrounding claim context, timing, and
ledger history differ. Any optimization must preserve claim order, refusal
semantics, tamper behavior, and append-only history, not just argv equality.

## Validation summary

The current exact-main worktree was revalidated with:

- `python -m pytest tests/ -q` → `274 passed`
- `python -m ruff check .` → `All checks passed!`
- `python -m showwork.cli verify --no-report` → `GREEN (49/112 verified)`
- `python -m showwork.cli audit --strict` → `RED (369/401 records chained, 4 fork(s))`

The strict audit is intentionally still red on current main and on the replay
receipt history, with the same four historical fork identities preserved. This
is consistent with the earlier base/head comparison above and with the current
merged-main raw-record counts.

## Boundaries

This report does not change source code, workflow files, schema, or release
controls. It records the evidence mismatch that keeps PR #30 held until the
source evidence PR is merged and the Vault closure report is amended to match
the exact merged-main truth.
