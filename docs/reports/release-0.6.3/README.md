# showwork 0.6.3 verification

`require` now builds a check from the same flags as `claim`. `--check-json`
stays valid. Shipped examples declare that check before the first claim.

The Cursor walk claimed first. After 0.6.0 that order rejected `require` and left
`finish` refused. 0.6.3 documents and accepts the flag form in the order the
gate already required.

`demo.png` is a Playwright capture of `demo.html` at 1280x720. Overflow checks
at 375, 768 and 1280 matched the viewport width. A generated HDR still added
extra slogans and was discarded.

| Requirement | Executable evidence |
| --- | --- |
| `require --type file_exists --path` records and can close | `tests/test_cli.py::test_require_accepts_claim_flags` |
| Behavior `require` accepts `--command-arg` | `tests/test_cli.py::test_require_accepts_command_flags_for_behavior` |
| Missing `--type` and `--check-json` exits | `tests/test_cli.py::test_require_needs_type_or_check_json` |
| `--check-json` still works | `tests/test_cli.py::test_require_check_json_still_works` |
| Claim then `require` stays refused | `tests/test_cli.py::test_require_after_claim_is_rejected` |
| README require line has flags and no `{` | `tests/test_quickstart.py::test_readme_require_uses_flags_before_claim` |
| Cursor walk requires before claim | `tests/test_quickstart.py::test_cursor_walk_requires_before_first_claim` |
| Agent prompt and Cursor rule match that order | `tests/test_quickstart.py` |
| Installed smoke uses flag `require` | `scripts/smoke_release.py` |
| Demo HTML has no horizontal overflow | Playwright at 375, 768 and 1280 pixels |

Limits: a passing check still only proves what it tests. showwork cannot
judge whether a requirement covers the request.

Candidate evidence is not publication. Owner steps after merge to main:

1. Confirm `pyproject.toml` version is `0.6.3`.
2. Tag `v0.6.3` on that commit.
3. Run the owner-gated publish workflow.
4. Create the GitHub release.
5. Post LinkedIn and X from the files in this folder.

Agents do not tag, publish, or post.

Sign-off: Cursor Grok | auto
