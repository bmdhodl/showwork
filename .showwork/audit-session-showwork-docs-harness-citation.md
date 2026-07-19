# Claims audit - session showwork-docs-harness-citation

**Verdict: YELLOW**  (2/3 verified)

- OK **README cites the Code as Agent Harness survey in a Where this sits section** (`file_contains`, RED)
    - /Where this sits/ found in README.md
- OK **SPEC.md carries a non-normative Background section citing arXiv 2605.18747** (`file_contains`, RED)
    - /arxiv.org/abs/2605.18747/ found in SPEC.md
- !! **full test suite passes after the doc change** (`command`, RED)
    - script not found: -m

## 1 gap(s) - a claimed 'done' is not real

- [RED/error] full test suite passes after the doc change - script not found: -m
