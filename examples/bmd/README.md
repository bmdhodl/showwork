# BMD desktop (supervisor)

BMD is a local control plane. showwork is the receipt engine. They stay
two processes: the agent writes `.showwork/` in the **user workspace**; the
BMD sidecar only reads.

This environment cannot write `bmdhodl/bmd-desktop` (private). Copy the
snippets below into that repo. Do not add `.showwork/` to the BMD git tree.

## Pin (from-scratch install)

`requirements.txt`:

```
showwork==0.4.0
```

The sidecar already vendors stdlib-only code. showwork has no runtime deps.
After the next showwork tag that includes `showwork.receipts`, you can import
it from the package. Until then, copy `src/showwork/receipts.py` beside
`lab/verification_badges.py` as `lab/showwork_receipts.py` and keep the
imports local.

PyInstaller (`packaging/bmd-server.spec`) `hiddenimports`:

```
showwork
showwork.cli
showwork.ledger
showwork.checks
showwork.audit
showwork.report
showwork.receipts
showwork.snapshot
showwork.hooks
showwork.scaffold
showwork.dashboard
showwork.control
showwork.guards
showwork.budgets
showwork.__main__
```

Skip `showwork.pytest_plugin`. Boot must not import a ledger. `/api/ping`
stays zero-work. Missing `.showwork/` is `unknown`, never green.

## Reader overlay

In `lab/verification_badges.py`, after the existing vault/frontmatter
resolution, join a run to receipts when it has `task_id` or `session`:

```python
from showwork.receipts import overlay_record

overlay = overlay_record(row, workspace_root)
if overlay is not None and overlay.get("state") != "unknown":
    return overlay
# else keep the vault fallback (Patrick profile)
```

Empty workspace: overlay is `unknown` ("No receipts yet.") so the badge stays
unknown. A prose-only finish is `claimed`. A failed check is `failed`.
Check-backed GREEN is `verified`.

The overlay never calls `start_session`, `record_claim`, or `finish_session`.

## Dispatch env and prompt

In `build_agent_prompt` / `launch_agent_session`, export:

```python
from showwork.receipts import agent_environ, agent_prompt_block, sidecar_interpreter

env = os.environ.copy()
env.update(agent_environ(workspace, task_id, interpreter=sidecar_interpreter()))
prompt = existing_prompt + "\n" + agent_prompt_block(
    task_id, interpreter=sidecar_interpreter(), agent=agent,
)
```

Pass `env` into the PTY spawn. Use `sidecar_interpreter()` (the frozen
`sys.executable`), not `python` on PATH.

Do not wrap with `showwork run --gate` on the first slice.

## States to assert in Playwright

- Empty workspace Home: UNKNOWN, copy "No receipts yet.", no VERIFIED badge.
- GREEN fixture: VERIFIED; click opens the claim text.
- Prose-only fixture: CLAIMED, not VERIFIED.
- Activity uses the same four states.
