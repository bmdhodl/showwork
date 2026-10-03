# Explicit snapshot exclusions

This source feature is pending a package release. Installed showwork 0.6.5 does
not have `start --ignore`.

A dashboard or a queue writer can change files while an agent works. Freeze
specific exclusions when you start a new session:

```bash
python -m showwork start --session fix-parser --agent codex --ignore data.json --ignore 'runs/**'
```

PowerShell uses the same command and quoting. Repeat `--ignore` for each path or
glob. Patterns use `/`, are case-sensitive, and stay relative to the workspace.
`*` and `?` stay within one path component. `runs/**` excludes that directory
and everything below it; `runs/*.jsonl` excludes only its immediate matching
files. Bracket classes and recursive wildcards in the middle are unsupported.
At most 32 patterns of 240 characters each are accepted. Git ignore rules do
not automatically change showwork's scope.

The receipt records the sorted exclusions at the first start and binds them
into the snapshot digest. Reopen with no `--ignore` to preserve that scope.
Supplying different exclusions refuses the start; use a new session for a
different contract. A changed or missing sidecar prevents a clean close and
prevents acceptance commands from running with the altered scope.

`verify --session fix-parser --json` includes `snapshot_scope`. Text output lists
the frozen exclusions. The Python and JavaScript read-only readers disclose
the same scope and validate its sidecar before qualifying recorded evidence.
Older readers that do not support `snapshot-exclusions-v1` cannot qualify it.

Command source evidence uses the same exclusions. A background write to
`data.json` can continue during a test command; a change to an unexcluded
source file still fails its before/after check. Exclusions are part of the
command's source hash and cache input, and do not suppress an explicit claim
or acceptance check that names an excluded file.

The damage guard compares files that existed at start. It checks unclaimed
edits and deletions, within its bounded scope. **New files are outside this
guard.** Declare checks for new deliverables and commit the receipt. A GREEN
result does not prove that requirements cover the request or excluded files.

Keep exclusions narrow. This option rejects ledger and Git targets, escaping
paths, and whole-workspace wildcards. The built-in generated-file exclusions
still apply. See the [snapshot contract](../SPEC.md#optional-frozen-snapshot-exclusions).
