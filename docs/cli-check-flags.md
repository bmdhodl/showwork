# require and claim check flags

`require` and `claim` share one flag surface. An unsupported combination is
rejected before a record is written. It is not stored and later ignored.

`--check-json` is an alternative to flags. Do not mix it with `--type` or with
the flags in the table.

Rejected checks exit `2`. That matches a refused requirement, not a generic
CLI crash.

## Supported flags

| `--type` | Required flags | Optional flags |
| --- | --- | --- |
| `file_exists` | `--path` | none |
| `file_contains` | `--path` `--pattern` | `--absent` |
| `path_moved` | `--from-path` `--to-path` | none |
| `frontmatter` | `--path` `--field` `--equals` | none |
| `glob_count` | `--pattern` `--op` `--n` | none |
| `command` | `--command-arg` (repeat) | `--expect-exit` `--stdout-contains` |
| `http_probe` | `--url` `--expect-status` | `--body-contains` |
| `git_state` | at least one of `--clean` `--branch` `--commit` | those same flags |

`--absent` belongs to `file_contains` only. It means the regex is not in the
file. It does not mean "this path is gone." There is no `file_exists --absent`.
A declared deletion is `path_moved`, or a later claim that names the path
after the snapshot check.

`--check-json` must use the same fields. Extra keys, including
`file_exists.absent`, are rejected.

The executable table is `tests/test_cli.py` (`test_file_exists_absent_flag_is_rejected`
and neighbors) and `tests/test_checks.py::test_validate_check_shape_rejects_file_exists_absent`.

## What each check class proves

| Kind | What it proves | What it does not prove |
| --- | --- | --- |
| Artifact check (`file_exists`, `file_contains`, `path_moved`, `frontmatter`, `glob_count`) | A path or glob in this tree matches the claim | That the application behaves correctly |
| Behavior acceptance (`command`) | A project Python script ran and matched exit/stdout | That the script tested the right thing |
| Integrity (`showwork audit`, JS reader) | The ledger chain hashes | That the checks were adequate, or that a signer attested the bytes |
| Current rerun (`verify` / `finish` now) | The named checks against this tree now | The historical close, unless you also read that close record |
| Read-only view (`receipts`, BMD overlay, JS audit) | What the ledger already contains | A fresh execution of command, Git, or network checks |

The original undeclared-delete hole from issue #64 is covered by
`tests/test_snapshot.py`. This page does not replace that snapshot check.
