# Claims audit - session pi-furnace-path-boundary-20260716

**Verdict: GREEN**  (2/2 verified)

- OK **Evidence paths are confined to the declared project root** (`file_contains`, RED)
    - /PathEscapeError/ found in src/showwork/checks.py
- OK **Adversarial path escape cases are covered by tests** (`file_contains`, RED)
    - /test_file_checks_reject_evidence_outside_project_root/ found in tests/test_checks.py
