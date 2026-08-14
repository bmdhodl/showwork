## What changed

<!-- Brief description of the change -->

## Verification

<!-- How did you verify this works? -->

- [ ] Tests pass locally (`pytest tests/ -q`)
- [ ] Claims recorded (`showwork verify --session <session-id>` exits 0)
- [ ] `.showwork/` receipts committed with this PR

## Checklist

- [ ] Changes are falsifiable (if claiming "done", a check can fail)
- [ ] Receipts committed - `.showwork/` ledger is part of the work
- [ ] Session closed through `showwork finish` (no `--no-verify` bypass)
- [ ] SPEC.md updated if the ledger format changed
- [ ] Tests green before commit

---

**For agent-authored PRs:** the session id is required. Human reviewers: verify
the receipts in `.showwork/` before merge.
