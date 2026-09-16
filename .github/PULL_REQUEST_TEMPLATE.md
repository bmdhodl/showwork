## Receipt

<!--
Required. Name the committed receipt file for the session that produced this
pull request. A pull request with no receipt is not reviewed.
See CONTRIBUTING.md.
-->

- Receipt path: `.showwork/sessions/<session-id>.jsonl`
- Session id: `<session-id>`
- Close verdict: <!-- ok | blocked -->

## What changed

<!-- Brief description of the change -->

## How to see it

<!-- The commands a reviewer runs to see this working. -->

```bash
python scripts/run_tests.py
python -m showwork.cli gate --session <session-id> --require-tracked
```

## Checklist

- [ ] Receipt committed - the `.showwork/` session and claims files are in this diff
- [ ] Session closed through `showwork finish` (no `--no-verify` bypass)
- [ ] Claims are falsifiable - a check can fail if the change is wrong
- [ ] Tests pass locally (`python scripts/run_tests.py`)
- [ ] SPEC.md updated if the ledger format changed
- [ ] Title starts with `agent:` if an agent produced this change

---

Human reviewers: read the receipt against the diff before merge.
