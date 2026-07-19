# showwork Claims Ledger Specification

**Specification version:** `spec-v0.2`

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
  claims-YYYY-MM-DD.jsonl
  sessions.jsonl
  audit-<label>.md
```

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
as verified proof. Severity is `RED` or `YELLOW`.

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

The check MUST [test: tests/test_checks.py::test_frontmatter] require a YAML-like
frontmatter block and exact scalar equality after quote trimming.

### `glob_count`

```json
{"type":"glob_count","pattern":"reports/*.md","op":">=","n":1}
```

Supported operators are `==`, `>=`, `<=`, `>`, and `<`. The check MUST [test:
tests/test_checks.py::test_glob_count] compare the actual match count with the
declared integer. Predicates that are true for every possible count, including
`>= 0` and `> -1`, MUST [test:
tests/test_checks.py::test_glob_count_rejects_vacuous] return an error.

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

## Integrity chain (`spec-v0.2`)

Append-only stops being a promise and becomes provable. Every record a
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

A conforming writer SHOULD mark ledger files `merge=union` in `.gitattributes`
so concurrent appends concatenate instead of producing conflict markers; union
merge preserves each side's line order, so every block's internal chain stays
intact.

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
{"event":"session.start","session":"deploy-fix","ts":"...","agent":"codex"}
{"event":"session.finish","session":"deploy-fix","ts":"...","status":"ok","claims_verdict":"GREEN"}
```

An explicit clean finish MUST [test:
tests/test_cli.py::test_exit_gate_refuses_red_close] verify that session's own
claims and refuse with exit code `2` when any active RED claim fails. A bypass
MUST [test: tests/test_cli.py::test_no_verify_bypass_is_stamped] remain visible
on the finish event. A Stop-hook adapter MUST [test:
tests/test_hooks.py::test_stop_hook_records_red_but_exits_zero] record the
verdict and unverified claims but exit zero because hooks observe rather than
gate.

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

An implementation conforms to `spec-v0.2` when:

- every normative requirement has a behavioral test named beside it;
- claims and retractions remain append-only;
- every appended record extends the integrity chain, and audits detect
  tampering, deletion, and unchained appends while accepting concurrent forks
  (a `prev` re-anchored to an earlier line) as GREEN and reporting them;
- all six checker semantics and anti-vacuous rules match this document;
- exit-gate and Stop-hook behavior remain distinct;
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
