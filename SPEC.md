# showwork Claims Ledger Specification

**Specification version:** `spec-v0.4`

This document defines a portable, append-only format for falsifiable agent
claims, deterministic verification, retractions, session lifecycle events, and
exit-gate verdicts. Normative terms follow RFC 2119.

An implementation can target this specification without using the Python
package.

## Storage and framing

Claims are UTF-8 JSON Lines. Records are separated by a line feed (`\n`) or a
carriage-return/line-feed pair (`\r\n`): a reader MUST [test:
tests/test_audit.py::test_line_boundaries_are_lf_or_crlf_only] split on `\r?\n`
and treat no other Unicode separator — U+2028, U+2029, U+0085, vertical tab,
form feed, the FS/GS/RS/US controls, or a lone carriage return — as a record
boundary, so one of them inside a JSON string keeps the record whole. Each
non-empty line is one complete JSON object in strict JSON; the bare tokens
`NaN`, `Infinity`, and `-Infinity` are not valid JSON, and a reader MUST [test:
tests/test_audit.py::test_nonstandard_json_constants_are_parse_errors] treat
such a line as a parse error rather than a live record. Writers MUST [test:
tests/test_spec_conformance.py::test_claims_are_jsonl_records] append records
without rewriting earlier lines. Readers SHOULD tolerate a UTF-8 BOM and blank
or comment lines. A parse error MUST [test:
tests/test_cli.py::test_unparseable_ledger_line_is_yellow_not_dropped] become a
visible non-GREEN result instead of disappearing.

The reference layout is:

```text
.showwork/
  sessions/<session-stem>.jsonl   one session's start / finish events
  claims/<session-stem>.jsonl     that session's claims and retractions
  snapshots/<session-stem>.json   tree snapshot taken at session.start
  claims-YYYY-MM-DD.jsonl         legacy shared day file (read, not written)
  sessions.jsonl                  legacy shared session file (read, not written)
  audit-<label>.md
```

New writes MUST [test:
tests/test_session_files.py::test_two_sessions_write_two_files] go to the
per-session files so two agents with distinct session ids never share a path.
Writers MUST [test:
tests/test_session_files.py::test_new_writes_do_not_touch_legacy_shared_files]
not append new records to the legacy shared files. Readers MUST [test:
tests/test_session_files.py::test_legacy_shared_files_remain_readable] still
load those leftover files. A session id MUST [test:
tests/test_session_files.py::test_session_file_stem_rejects_path_escape] become
a single path component matching `[A-Za-z0-9._-]{1,120}` before it is joined;
empty ids, `.`, `..`, and path separators are rejected or rewritten, never
used as directory traversal. When rewrite or truncation would map two distinct
ids onto one stem, the writer MUST [test:
tests/test_session_files.py::test_session_file_stem_rejects_path_escape] prefix
the stem with `h-` and a short hash of the original id so the mapping stays
injective and hashed stems cannot collide with an exact id on a
case-insensitive filesystem. Distinct session files MUST [test:
tests/test_session_files.py::test_two_agent_session_files_git_merge_without_conflict]
merge in git without a same-path conflict. When one session spans more than
one claims file, readers MUST [test:
tests/test_session_files.py::test_split_session_files_honor_later_retraction]
keep the current write-path file last and MUST [test:
tests/test_session_files.py::test_append_order_inside_file_beats_timestamp]
keep append order inside each file. Writers MUST [test:
tests/test_session_files.py::test_writer_reuses_existing_session_file]
append to an existing leftover file for that session when the current stem
has no file yet. A current stem file that already belongs to a different
session MUST [test:
tests/test_session_files.py::test_writer_refuses_current_file_owned_by_another_session]
be refused. Linked worktrees MUST [test:
tests/test_run.py::test_linked_worktree_receipt_is_written_in_worktree] write
receipts in that worktree's own `.showwork/` so the receipt ships with the
branch.

Two agents that reuse the same session slug still share one file. Give each
agent a distinct slug (`cursor-fix-nav`, `codex-fix-nav`).

## Claim record

```json
{
  "session": "deploy-fix",
  "ts": "2026-07-10T14:30:00",
  "claim": "the configuration contains the new timeout",
  "severity": "RED",
  "artifact": "config/api.yaml",
  "check": {
    "type": "file_contains",
    "path": "config/api.yaml",
    "pattern": "timeout: 30"
  }
}
```

`session`, `ts`, `claim`, and `severity` identify the assertion and its impact.
`artifact` is optional. `check` is optional; a claim without one MUST [test:
tests/test_checks.py::test_no_check_is_skipped] remain recorded but cannot count
as verified proof. A writer MUST [test:
tests/test_checks.py::test_claim_rejects_file_exists_without_path] reject a
check at claim time when required fields for that type are missing. The Python
`record_claim` writer MUST [test:
tests/test_checks.py::test_record_claim_rejects_file_exists_without_path] apply
the same shape check. An omitted check (`None`) is prose. An explicitly
supplied check, including `{}`, MUST [test:
tests/test_checks.py::test_record_claim_rejects_empty_check] go through that
shape check. Severity is `RED` or `YELLOW`.

## Check semantics

All relative paths resolve from the declared project root.

### `file_exists`

```json
{"type":"file_exists","path":"reports/result.md"}
```

The check MUST [test: tests/test_checks.py::test_file_exists_pass] pass only
when `path` is a regular file and MUST [test:
tests/test_checks.py::test_file_exists_fail] fail when it is missing.

### `file_contains`

```json
{"type":"file_contains","path":"config/api.yaml","pattern":"timeout: 30","absent":false}
```

`pattern` is a regular expression. Positive checks MUST [test:
tests/test_checks.py::test_file_contains_pass_and_fail] pass only on a match.
When `absent` is true, the check MUST [test:
tests/test_checks.py::test_file_contains_absent] pass only when the pattern does
not match. Invalid regular expressions and positive expressions that match the
empty string MUST [test:
tests/test_checks.py::test_file_contains_rejects_vacuous_pattern] return an
error, never proof.

Evaluation is bounded. A pattern that does not finish inside the time limit
MUST [test:
tests/test_checks.py::test_file_contains_catastrophic_pattern_cannot_hang]
return an error, and a file above the scan cap MUST [test:
tests/test_checks.py::test_file_contains_rejects_oversize_file] return an error.
Both are errors rather than failures, because a pattern that never finishes
proves nothing either way. This exists because the party that supplies the
pattern is sometimes the party that supplies the file: on a fork pull request,
an expression like `(a+)+$` against a wall of `a` characters would otherwise pin
a CPU on the verification host until the job timed out.

### `path_moved`

```json
{"type":"path_moved","from":"Queue/task.md","to":"Queue/Complete/task.md"}
```

The check MUST [test: tests/test_checks.py::test_path_moved] pass only when the
source is absent and the destination exists.

### `frontmatter`

```json
{"type":"frontmatter","path":"Queue/task.md","field":"status","equals":"done"}
```

The check MUST [test: tests/test_checks.py::test_frontmatter_requires_exact_delimiter_lines]
require a YAML-like frontmatter block bounded by exact opening and closing
delimiter lines (`---`), and exact scalar equality after quote trimming.

### `glob_count`

```json
{"type":"glob_count","pattern":"reports/*.md","op":">=","n":1}
```

Supported operators are `==`, `>=`, `<=`, `>`, and `<`. The check MUST [test:
tests/test_checks.py::test_glob_count] compare the actual match count with the
declared integer. Predicates that are true for every possible count, including
`>= 0` and `> -1`, MUST [test:
tests/test_checks.py::test_glob_count_rejects_vacuous] return an error.

Recursive glob components are not supported in verifier context. The pattern MUST
[test: tests/test_checks.py::test_glob_count_rejects_recursive_pattern] reject any
`glob_count` claim whose pattern includes an exact `**` component with status
`error` before attempting match traversal. This is an explicit refusal boundary:
recursive claims may not silently downgrade into a bounded-count comparison.

Verifier-context `glob_count` uses a deterministic non-recursive traversal inspection limit of `MAX_GLOB_TRAVERSAL` (100000 inspected directory entries). If traversal would exceed that limit, the checker returns a verifier error/refusal rather than comparing a partial or actual count.

### `command`

```json
{"type":"command","argv":["python","scripts/run_tests.py"],"expect_exit":0,"stdout_contains":"passed"}
```

The command checker is intentionally locked. It MUST [test:
tests/test_checks.py::test_command_happy_path] execute without a shell and
compare the exit code plus optional output text. It MUST [test:
tests/test_checks.py::test_command_lock_rejects_non_python] allow only a Python
interpreter followed by a script under the project root. It MUST [test:
tests/test_checks.py::test_command_lock_rejects_shell_meta] reject shell
metacharacters, MUST [test:
tests/test_checks.py::test_command_lock_rejects_powershell] reject shell scripts,
MUST [test: tests/test_checks.py::test_command_lock_rejects_escape] reject root
escape, and MUST [test:
tests/test_checks.py::test_command_recursion_guard] reject nested command
verification.

### `http_probe`

```json
{"type":"http_probe","url":"https://example.com/health","expect_status":200,"body_contains":"ok"}
```

The checker MUST [test: tests/test_checks.py::test_http_probe_happy_path] accept
only `http` and `https` URLs with a hostname, no userinfo or fragment, and an
integer expected status from 100 through 599. The optional `body_contains` value
MUST [test: tests/test_checks.py::test_http_probe_validates_url_and_inputs] be a
non-empty string when present. The checker MUST [test:
tests/test_checks.py::test_http_probe_status_and_body_mismatches] compare the
observed status exactly and, when requested, require the exact UTF-8 byte
substring in the bounded response body. An HTTP error status is still a response
that can satisfy a claim MUST [test:
tests/test_checks.py::test_http_probe_accepts_expected_http_error_status], while
a redirect MUST [test: tests/test_checks.py::test_http_probe_does_not_follow_redirects]
remain un-followed. A response larger than the checker cap MUST [test:
tests/test_checks.py::test_http_probe_rejects_oversized_response] return an error.
When `SHOWWORK_NO_NETWORK` is set, the checker MUST [test:
tests/test_checks.py::test_http_probe_disabled_by_no_network_env] refuse the
request and return an error.

### `git_state`

```json
{"type":"git_state","clean":true,"branch":"main","commit":"1243490"}
```

The checker MUST [test: tests/test_checks.py::test_git_state_requires_non_vacuous_expectation]
require at least one of `clean`, `branch`, or `commit`. It MUST [test:
tests/test_checks.py::test_git_state_validates_fields] reject a non-boolean
`clean`, an empty branch, and a commit value that is not a hexadecimal prefix
of at least seven characters. A `clean` assertion MUST [test:
tests/test_checks.py::test_git_state_detects_dirty_tree_and_mismatches] compare
the working tree's tracked and untracked status exactly. A `branch` assertion
MUST [test: tests/test_checks.py::test_git_state_detects_dirty_tree_and_mismatches]
compare the current branch name exactly, and a `commit` assertion MUST [test:
tests/test_checks.py::test_git_state_happy_path] pass when HEAD starts with the
declared hexadecimal prefix. A non-repository root or failed Git query MUST
[test: tests/test_checks.py::test_git_state_errors_outside_repository] return
an error.

## Integrity chain (`spec-v0.2`)

Append-only stops being a promise and becomes provable. Chain hashing is
unchanged from `spec-v0.2`. Every record a
writer appends MUST [test: tests/test_audit.py::test_append_adds_prev_hash]
carry a `prev` field: the SHA-256 hex digest of the previous record line in
the same file, or of the genesis anchor `showwork:genesis:<filename>` when
the file has no prior record.

```json
{"session":"s","ts":"...","claim":"...","severity":"RED","prev":"<sha256 of previous record line>"}
```

Hashing covers the record line's stripped content. It MUST [test:
tests/test_audit.py::test_chain_survives_eol_rewrite] be end-of-line
agnostic, so a checkout or editor that rewrites line endings does not break
the chain while any content change does. Blank and comment lines are not
records and do not participate.

An auditor walks each file and re-derives the chain. A record's `prev` is
valid when it matches the hash of **any earlier record line in the same file**,
or the genesis anchor. The common case is the immediate predecessor (a linear
step). A `prev` that matches an earlier but non-immediate line is a *fork*, not
a break (see *Concurrent branches* below). A `prev` that matches **no earlier
line** MUST [test: tests/test_audit.py::test_tamper_detected_at_exact_line]
report a break, naming the first affected line — this is exactly what
modification produces; the auditor MUST [test:
tests/test_audit.py::test_deleted_line_is_detected] detect a deleted record and
MUST [test: tests/test_audit.py::test_fork_does_not_hide_tampering] detect
tampering inside a forked file the same way. Because an anchor must resolve to
an *earlier* line, reordering a record before its anchor is also a break. A
record without `prev` appearing after the chain has started MUST [test:
tests/test_audit.py::test_unchained_after_chain_start_is_red] be a break:
append-only can no longer be shown for that file.

### Concurrent branches (forks)

Two sessions appending concurrently in separate worktrees, then merged, produce
a fork: two record blocks whose `prev` points at the same earlier line. This is
legitimate concurrency, not tampering, so an auditor MUST [test:
tests/test_audit.py::test_concurrent_merge_audits_green_with_forks] accept a
record whose `prev` re-anchors to an earlier line, count it as a fork, keep the
file's verdict GREEN, and report the fork count with each *branch head* (a
record line that no other record anchors to) so the fork is never silent. Two
independent chains sharing a file — each first record anchored to genesis — are
a fork of two roots, handled the same way [test:
tests/test_audit.py::test_two_genesis_roots_is_a_fork_not_a_break].

A conforming writer SHOULD give each agent a distinct session slug so each
writer has its own file. Leftover shared files MAY be marked `merge=union` in
`.gitattributes` so concurrent appends concatenate instead of producing
conflict markers; union merge preserves each side's line order, so every
block's internal chain stays intact. `merge=union` is not a substitute for
per-session files.

Fork tolerance preserves tamper-evidence and gives up only linearity: a forked
file has more than one head, so deleting a whole branch tip is undetectable from
the file alone — as deleting the single tip of a linear chain always was.
Publishing every head (each is exposed in the audit output) closes that gap per
branch. An auditor MAY offer a strict mode that treats any fork as RED [test:
tests/test_audit.py::test_strict_forbids_forks] for repositories that forbid
concurrent sessions and want the single-history guarantee. The full rationale is
in [docs/concurrency.md](docs/concurrency.md).

Records that predate the chain (`spec-v0.1` ledgers) are *pre-chain*.
A file containing only pre-chain records MUST [test:
tests/test_audit.py::test_pre_chain_records_are_anchored] not audit
GREEN — integrity is unprovable, which is YELLOW, never a silent pass. The
first chained append anchors everything above it: from that point tampering
with a pre-chain record MUST [test:
tests/test_audit.py::test_pre_chain_records_are_anchored] break the chain.

The hash of a file's last record is its *head*. An auditor MUST [test:
tests/test_audit.py::test_head_hash_reported] expose the head so it can be
published out-of-band (a commit message, a post, a printout); a published
head anchors the entire history behind it. The reference CLI exposes all of
this as `showwork audit`, exiting 0/3/2 for GREEN/YELLOW/RED [test:
tests/test_audit.py::test_cli_audit_exit_codes]; `showwork audit --strict`
turns any fork RED [test: tests/test_audit.py::test_cli_audit_strict_exit_code].

## Retractions

History is never edited. A correction appends a referencing record:

```json
{
  "session":"deploy-fix",
  "ts":"2026-07-10T14:31:00",
  "retracted":true,
  "retracts":{"session":"deploy-fix","claim":"the configuration changed"},
  "retraction_reason":"the write failed"
}
```

A later referencing retraction MUST [test:
tests/test_checks.py::test_append_only_retraction] suppress the target from the
active verdict without removing the original record. Inline `retracted: true`
claims MAY be read for compatibility.

## Session lifecycle and exit gate

Session events use the same JSONL framing:

```json
{"event":"session.start","session":"deploy-fix","ts":"...","agent":"codex","tree_snapshot":{"count":12,"sha256":"..."}}
{"event":"session.finish","session":"deploy-fix","ts":"...","status":"ok","claims_verdict":"GREEN"}
```

A `session.start` MUST [test:
tests/test_snapshot.py::test_start_records_tree_snapshot] record
`tree_snapshot` with `count` and `sha256` for a sidecar at
`.showwork/snapshots/<stem>.json`. The sidecar is not a JSONL chain file.
`verify --session` and a clean `finish` MUST [test:
tests/test_snapshot.py::test_undeclared_delete_is_red] fail RED when a file
that existed at start is gone or its content hash changed, and no active
claim named that path (`path`, `from`, `to`, `artifact`, or a relative
`command` argv path). New files created after start are out of this check.
Sessions whose start event has no `tree_snapshot` MUST [test:
tests/test_snapshot.py::test_legacy_session_without_snapshot_skips] skip
this check so older ledgers stay readable. A missing or digest-mismatched
sidecar for a start that declared `tree_snapshot.sha256` MUST [test:
tests/test_snapshot.py::test_missing_snapshot_is_red] fail RED. A named
path MAY [test: tests/test_snapshot.py::test_declared_path_may_change]
change. `.showwork/` is excluded from the snapshot.

A file under `.showwork/artifacts/<stem>/` that no active claim names MUST
[test: tests/test_snapshot.py::test_unreferenced_artifact_warns_but_does_not_refuse]
produce a YELLOW result. Such a file ships with the change and proves
nothing, but it damages nothing either, so it warns and never refuses a
clean close. A file in that directory that an active claim does name MUST
[test: tests/test_snapshot.py::test_cited_artifact_does_not_warn] produce no
such result. The directory is walked directly, because files created after
start are out of the snapshot check and `.showwork/` is excluded from it.
Such a result is synthetic and MUST [test:
tests/test_snapshot.py::test_unreferenced_artifact_alone_is_not_minimum_proof]
NOT satisfy the minimum-proof requirement of a clean close. An artifacts path
that resolves outside the ledger MUST [test:
tests/test_snapshot.py::test_escaping_artifacts_path_does_not_skip_the_undeclared_gate]
fail RED without skipping the undeclared-change check.

An explicit clean finish MUST [test:
tests/test_cli.py::test_exit_gate_refuses_red_close] verify that session's own
claims and refuse with exit code `2` when any active RED claim fails. A clean
finish MUST [test: tests/test_cli.py::test_exit_gate_refuses_empty_session]
also refuse when the session has no check-backed claims (prose-only or empty
is not proof). A refused finish MUST [test:
tests/test_cli.py::test_refused_finish_records_claims_unverified] stamp
`claims_unverified` (and `refuse_reason` when applicable) on the event. A
bypass MUST [test: tests/test_cli.py::test_no_verify_bypass_is_stamped] remain
visible on the finish event. A blocked finish MUST [test:
tests/test_cli.py::test_blocked_close_stamps_claims_verdict] stamp
`claims_verdict` without refusing the close. A Stop-hook adapter MUST [test:
tests/test_hooks.py::test_stop_hook_records_red_but_exits_zero] record the
verdict and unverified claims but exit zero because hooks observe rather than
gate. When `SHOWWORK_SESSION` is set, the Stop hook MUST [test:
tests/test_hooks.py::test_stop_hook_prefers_showwork_session_env] bind to that
id and stamp `session_bound_from`; otherwise it MUST [test:
tests/test_hooks.py::test_stop_hook_marks_unbound_payload_session] stamp
`session_unbound` on the observed finish. A gated `run` MUST [test:
tests/test_run.py::test_run_gate_refuses_success_with_no_claims] refuse with
exit 2 when the wrapped command exits 0 without check-backed claims, matching
the finish gate.

## Verdict algebra

- `RED`: at least one active failed claim has RED severity.
- `YELLOW`: no RED failure exists, but a YELLOW claim fails or a checker errors.
- `GREEN`: no active claim fails or errors. Unchecked prose is recorded but does
  not count as verified.

The evaluator MUST [test:
tests/test_checks.py::test_verdict_red_yellow_green] apply those severity rules.
Checker errors MUST [test:
tests/test_checks.py::test_checker_error_is_yellow] prevent a GREEN verdict.

## Conformance

An implementation conforms to `spec-v0.4` when:

- every normative requirement has a behavioral test named beside it;
- new writes use per-session files and leftover shared files remain readable;
- claims and retractions remain append-only;
- every appended record extends the integrity chain, and audits detect
  tampering, deletion, and unchained appends while accepting concurrent forks
  (a `prev` re-anchored to an earlier line) as GREEN and reporting them;
- all eight checker semantics and anti-vacuous rules match this document;
- exit-gate and Stop-hook behavior remain distinct;
- sessions with `tree_snapshot` fail RED on undeclared deletes and edits;
- artifact files no active claim names warn YELLOW without refusing a close;
- parse and checker errors stay visible.

A reader-only implementation (an auditor that verifies chains and computes
verdicts without writing) MAY declare conformance to the reading half of
this specification; it SHOULD state which checker types it re-executes and
report the rest as errors rather than silently skipping them.

Implementations SHOULD publish their conformance suite and the specification
version they target.

## Background (non-normative)

Nothing in this section is a requirement. It records why the format is shaped
the way it is, for implementers deciding whether the constraints are arbitrary.

Three design choices carry the weight, and each is a deliberate refusal:

1. **A claim without a `check` is never proof.** Natural-language completion
   reports are the failure mode this format exists to catch. They are recorded
   for context and excluded from the verdict.
2. **No model evaluates the record.** Every checker is deterministic and
   re-executable by a third party who does not trust the writer. A verdict that
   requires inference to reproduce is not audit-grade.
3. **The exit gate refuses rather than warns.** A gate that reports a problem
   and closes anyway trains everyone to ignore it.

The 2026 survey [*Code as Agent Harness*](https://arxiv.org/abs/2605.18747)
(Ning et al., arXiv:2605.18747) describes the same boundary from the research
side. Its §3.4.4 treats compiler, runtime, and test signals as "deterministic
sensors" that are "reproducible enough to serve as control signals," and holds
that agentic critique "should interpret sensor outputs rather than replace
them." Choice 2 above is that rule applied to an agent's self-reported
completion. Its §5.2.5 argues that safety and accountability belong in harness
state rather than in a model's instructions, which is what an append-only
ledger with a refusing gate provides.

The survey predates this specification and does not reference it; it is cited
as independent framing for the problem, not as endorsement.
