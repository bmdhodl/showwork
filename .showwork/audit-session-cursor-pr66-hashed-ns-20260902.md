# Claims audit - session cursor-pr66-hashed-ns-20260902

**Verdict: RED**  (2/3 verified)

- XX **lossy stems use the h- hashed namespace** (`file_contains`, RED)
    - /prefix = f" h- -encodedCommand ZABpAGcAZQBzAHQA -\ -inputFormat xml -outputFormat text/ NOT in src/showwork/ledger.py
- OK **hashed stems cannot collide with an exact lookalike** (`file_contains`)
    - /foo_hashed.lower\(\) != session_file_stem\(lookalike\).lower\(\)/ found in tests/test_session_files.py
- OK **test suite passes** (`command`)
    - exit 0, stdout has 'passed'

## 1 gap(s) - a claimed 'done' is not real

- [RED/fail] lossy stems use the h- hashed namespace - /prefix = f" h- -encodedCommand ZABpAGcAZQBzAHQA -\ -inputFormat xml -outputFormat text/ NOT in src/showwork/ledger.py
