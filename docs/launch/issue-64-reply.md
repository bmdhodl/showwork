# Issue #64 reply (draft only)

Paste this as the owner. Do not post it from an agent account.

---

You are right on both counts.

`verify` GREEN 1/1 and `audit` GREEN 2/2 were correct for 0.3.0: the chain was intact, and the `path_moved` claim was true. The verdict only covers what the session declared. The ledger had no prior state, so an undeclared delete could not fail.

That was a hole, not a documented design choice. spec-v0.4 closes it.

`session.start` now snapshots the project tree (content hashes, excluding `.showwork/` and other junk dirs). `verify --session` and `finish --status ok` go RED if a file that existed at start is gone or changed and no active claim named that path (`path`, `from`, `to`, `artifact`, or a relative command script). New files created after start are out of this check. Sessions recorded before this change have no `tree_snapshot` on start and skip the check, so old ledgers stay readable.

On 0.3.0 from PyPI you will still see GREEN. The tree is 0.4.0 and is not on PyPI yet.

Thanks for filing this. It is the only inbound issue the project has, and it was a real one.
