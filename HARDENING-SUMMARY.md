# showwork v0.2 hardening summary

**Stop condition (a):** **25 solid draft PRs** opened with red→green tests, full suite green, dogfood receipts. Never merged to `main` by this loop.

**Date:** 2026-07-17  
**Not committed to `main`.** This file is the stop artifact only.

## Draft PRs opened

| # | Branch | Title | Failure class / lens |
|---|--------|-------|----------------------|
| [2](https://github.com/bmdhodl/showwork/pull/2) | `grok/harden-reclaim-after-retract` | append-only retraction must not kill later re-claims | Exit-gate / retraction |
| [3](https://github.com/bmdhodl/showwork/pull/3) | `grok/harden-invalid-check-json` | invalid `--check-json` raises clean SystemExit | CLI ergonomics |
| [5](https://github.com/bmdhodl/showwork/pull/5) | `grok/harden-utf8-ledger-decode` | non-UTF-8 ledger (older approach) | Ledger integrity *(superseded on current main by #24)* |
| [6](https://github.com/bmdhodl/showwork/pull/6) | `grok/harden-audit-report-path-escape` | keep verify audit reports inside `.showwork/` | Path escape / Windows |
| [7](https://github.com/bmdhodl/showwork/pull/7) | `grok/harden-frontmatter-bool-equals` | frontmatter equals accepts JSON booleans | Checker correctness |
| [8](https://github.com/bmdhodl/showwork/pull/8) | `grok/harden-finish-status-case` | finish_session treats status OK as ok | Exit-gate |
| [9](https://github.com/bmdhodl/showwork/pull/9) | `grok/harden-claims-date-path-escape` | claims date must be YYYY-MM-DD | Path escape |
| [10](https://github.com/bmdhodl/showwork/pull/10) | `grok/harden-non-object-ledger-line` | non-object JSONL lines are YELLOW | Hostile ledger |
| [11](https://github.com/bmdhodl/showwork/pull/11) | `grok/harden-file-exists-directory-detail` | file_exists directory not "missing" | Checker messaging |
| [12](https://github.com/bmdhodl/showwork/pull/12) | `grok/harden-non-dict-check-field` | non-dict check field is error | Hostile claim shape |
| [13](https://github.com/bmdhodl/showwork/pull/13) | `grok/harden-empty-glob-pattern` | empty glob clear error | Checker / CLI |
| [14](https://github.com/bmdhodl/showwork/pull/14) | `grok/harden-file-contains-directory-detail` | file_contains/frontmatter non-file | Checker messaging |
| [15](https://github.com/bmdhodl/showwork/pull/15) | `grok/harden-command-stdout-contains-type` | stdout_contains must be string | Checker types |
| [16](https://github.com/bmdhodl/showwork/pull/16) | `grok/harden-file-contains-pattern-type` | pattern must be string | Checker types |
| [17](https://github.com/bmdhodl/showwork/pull/17) | `grok/harden-path-moved-path-types` | path fields must be strings | Checker types |
| [18](https://github.com/bmdhodl/showwork/pull/18) | `grok/harden-frontmatter-field-type` | field must be non-empty string | Checker types |
| [19](https://github.com/bmdhodl/showwork/pull/19) | `grok/harden-readme-spec-version` | README links spec-v0.2 | Docs |
| [20](https://github.com/bmdhodl/showwork/pull/20) | `grok/harden-path-moved-empty-paths` | path_moved empty from/to vacuous pass | Checker correctness (**false proof**) |
| [21](https://github.com/bmdhodl/showwork/pull/21) | `grok/harden-glob-n-type` | glob_count.n must be integer | Checker types |
| [22](https://github.com/bmdhodl/showwork/pull/22) | `grok/harden-audit-file-not-a-file` | audit_file missing/dir YELLOW | Audit API crash |
| [23](https://github.com/bmdhodl/showwork/pull/23) | `grok/harden-command-expect-exit-type` | expect_exit must be integer | Checker types |
| [24](https://github.com/bmdhodl/showwork/pull/24) | `grok/harden-utf8-read-no-crash` | invalid UTF-8 non-GREEN (current framing) | Ledger integrity |
| [25](https://github.com/bmdhodl/showwork/pull/25) | `grok/harden-empty-check-path` | empty paths are errors | Path / messaging |
| [26](https://github.com/bmdhodl/showwork/pull/26) | `grok/harden-invalid-severity-defaults-red` | invalid severity → RED for gate | Exit-gate (**false clean close**) |
| [27](https://github.com/bmdhodl/showwork/pull/27) | `grok/harden-hook-session-id-type` | stop-hook session_id type guard | Hooks / ledger pollution |

All draft; none merged by the hardening loop. Each includes red→green test(s) and dogfood `.showwork/` on the branch.

## Failure classes found

1. **Exit-gate holes** — re-claim after retract skipped forever; `status="OK"` bypass; invalid severity demotes RED fails to YELLOW so finish succeeds.
2. **Vacuous false proofs** — `path_moved` with empty `to` passed by resolving to project root.
3. **Hostile ledger crashes** — invalid UTF-8, non-object JSONL, non-dict `check` → AttributeError/UnicodeDecodeError taking down verify/finish/append.
4. **Path escape** — session labels and `--date` wrote/read outside `.showwork/`.
5. **Type/shape validation** — paths, patterns, fields, `n`, `expect_exit`, `stdout_contains` raw exceptions.
6. **Misleading checker messages** — directories reported as "missing"; empty path as " missing".
7. **CLI UX** — malformed `--check-json` traceback.
8. **Docs drift** — README still pointed at spec-v0.1.
9. **Hooks** — non-scalar `session_id` became str()-mangled session names.

## Top 5 residual gaps (next to fix)

1. **Deterministic concurrent append locking** — TOCTOU on prev hash; needs controlled race test or advisory lock without flaking.
2. **Session-scoped verify vs day-file encoding errors** — synthetic UTF-8 error records lack `session`, so `verify --session` can stay GREEN while the day file is YELLOW.
3. **`run --gate` with 0 claims** — success with GREEN 0/0; PROPOSAL if product wants ≥1 verified pass for clean wrap.
4. **Shared sanitize helper** for all label-derived filenames (report path + date already split across PRs).
5. **Merge #5 vs #24** — prefer #24 (matches current `read_record_text` framing); close or restack #5 to avoid conflict.

## Blockers

None. Full suite green on `main` baseline throughout (~94–97 tests). Publishing/merge remains owner-gated.

## Evidence

- Scratch: `C:\Users\patri\AppData\Local\Temp\grok-goal-b2fc7844fb97\implementer\` (`prs.txt`, `pytest-full-*.txt`, `repro-*.txt`)
- Per-branch dogfood sessions: `showwork-harden-*` in `.showwork/`
