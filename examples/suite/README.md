# Read runtime and acceptance evidence separately

This offline example is selected for showwork #102/#103/#70. The
[contract and compatibility matrix](../../docs/suite-evidence.md) describe the
source-built package pins, existing fields and remaining limits.

`read_evidence.py` needs the installed validation showwork wheel. It has no
AgentGuard dependency: the runtime input is AgentGuard's existing JSON receipt
and matching trace. It reads named requirements and command references without
running a command, writing a ledger or granting permission.

```console
python scripts/check_suite_installed.py --artifacts NEW_DIRECTORY
```

Run that command from the repository root. It builds separate validation wheels
and environments, proves actual SDK denial before a second local provider stub
call, and leaves the generated `workspace/.showwork/`, runtime traces and
`proof.json` in the new directory. The output names the source revisions and wheel
hashes. These are validation artifacts, not new published releases.

The failed attempt remains beside the corrected attempt. A runtime stop cannot
hide task failure, and a successful acceptance result authorizes no further call.
The reader's output is an ephemeral example, not a persisted cross-product schema
or supported SDK API. BMD implementation stays on its existing receipt owner and
selected roadmap task.
