# Claims audit - session v02-phase-1

**Verdict: RED**  (3/5 verified)

- OK **every ledger append now carries a prev hash (integrity chain)** (`file_contains`, RED)
    - /record\["prev"\] = _prev_hash/ found in src/showwork/ledger.py
- OK **showwork audit verifies chains, names exact break lines, exposes head hashes** (`file_contains`, RED)
    - /def audit_file/ found in src/showwork/audit.py
- .. **spec bumped to v0.2 with a test-anchored Integrity chain section** (`None`, RED)
    - retracted: shell backtick expansion mangled the regex pattern at record time; re-recording with a correct pattern
- OK **full test suite passes including tamper-detection tests** (`command`, RED)
    - exit 0
- XX **spec bumped to v0.2 with a test-anchored Integrity chain section (corrected)** (`file_contains`, RED)
    - /Integrity chain .spec-v0\.2./ NOT in SPEC.md

## 1 gap(s) - a claimed 'done' is not real

- [RED/fail] spec bumped to v0.2 with a test-anchored Integrity chain section (corrected) - /Integrity chain .spec-v0\.2./ NOT in SPEC.md
