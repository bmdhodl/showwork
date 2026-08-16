# showwork integrity-command-replay design

Date: 2026-08-16

Scope: evidence-only. No product, workflow, schema, or release change.

## Blocking finding

This report exists because PR #30 was incorrectly worded as if the replay
receipt evidence were already durably closed. It is not. The merged replay
receipt artifact is only the narrow 2/2 session proof; it does not by itself
ground the broader raw-count history, the hosted strict-step timing, or the
semantic/refusal matrix that the closure wording must preserve.

The source evidence lane therefore keeps the card evidence-driven and
separates:

- the local-only historical owner snapshot,
- the reviewed replay receipt head,
- the current merged main truth, and
- the disposable semantic/refusal matrix.

## Raw-record comparison

The raw-record method is explicit: iterate every `.showwork/claims-*.jsonl`
file in the named commit, count records whose `check.type` is `command`, and
separately count exact `argv == ["python", "scripts/run_tests.py"]`.

```powershell
@'
import json
import subprocess
from collections import Counter

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
same thing as the merged main ledger. The report therefore does not treat
`95/91` as current main truth; the merged main truth is bound to
`2c6655cb684a73084dd32cd0a3ebbfe243ef13fd` and its raw counts above.

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
an observed hosted duration. It is superseded by the observed strict-step
window above.

## Semantic and refusal matrix

The disposable matrix for this lane is the minimal pair already proven in the
session artifact and preserved for closure reasoning:

| Case | Command / check | Result |
|---|---|---|
| Refusal boundary | `SHOWWORK_NO_COMMANDS` file contains guard text | GREEN |
| Replay command execution | `python scripts/run_tests.py` | GREEN exit 0 |

This matrix is intentionally small. It proves the refusal boundary and the
successful replay command without pretending the command text is a safe cache
key.

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
receipt history, with the same four historical fork identities preserved.
This is consistent with the earlier base/head comparison above and with the
current merged-main raw-record counts.

## Boundaries

This report does not change source code, workflow files, schema, or release
controls. It records the evidence mismatch that keeps PR #30 held until the
source evidence PR is merged and the Vault closure report is amended to match
the exact merged-main truth.
