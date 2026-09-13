# Claims audit - session cursor-bmd-vault-card

**Verdict: GREEN**  (6/6 verified)

- OK **BMD overlay tracked as a vault request, not GitHub Projects** (`file_exists`)
    - docs/requests/bmd-overlay-receipts.md exists
- OK **vault card tracker is vault** (`frontmatter`)
    - tracker=vault
- OK **vault card refuses GitHub Projects** (`frontmatter`)
    - github_project=none
- OK **BMD example points at the vault Requests folder** (`file_contains`)
    - /Requests/bmd-overlay-receipts.md/ found in examples/bmd/README.md
- OK **todo tracks BMD work as a vault request** (`file_contains`)
    - /docs/requests/bmd-overlay-receipts.md/ found in todo.md
- OK **tests still pass** (`command`)
    - exit 0, stdout has 'passed'
