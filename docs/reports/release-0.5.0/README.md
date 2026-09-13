# showwork 0.5.0 release audit

Audit date: 2026-09-13. Scope: Python runtime, CLI, ledger and snapshot boundaries,
claim checkers, subprocess lifecycle, pytest plugin, supervisor receipts API,
JavaScript conformance, packaging, release workflow, and open issues/PRs.

## Reproduced and fixed

- Eight invalid budget configurations were accepted (NaN, infinity, booleans,
  fractional call ceilings). They now fail validation.
- Reopening a session replaced its damage baseline. Original snapshot bytes
  and their anchor now survive reopening. The installed 0.4.0 versus candidate
  0.5.0 comparison is in the adjacent demo JSON and `examples/restart_demo.py`.
- Snapshot-directory symlinks could redirect writes outside the ledger.
  Resolved containment is enforced on writes and verification.
- Proposed PR #68's supervisor reader could execute a claimed workspace Python
  script and did not check chain integrity. The integrated reader allows only
  filesystem checks and refuses to award VERIFIED to unaudited integrity.
- A shared pytest-last.json let other sessions overwrite proof. Each session
  now has its own artifact; a later failed run of that session invalidates it.
- A timed-out wrapped process left descendants running. A real grandchild
  reproduced a write after timeout. Process-tree termination prevents it.
- Publishing accepted arbitrary v* sources. Real Git fixtures now bind a
  semantic version tag to current origin/main, HEAD, and package metadata.

## Verification

- Full Python suite: 387 passed before final release documentation preparation.
- JavaScript auditor: 16 checks passed, including tampering and frozen fixtures.
- Installed wheel smoke on Python 3.10.11 and 3.13.2: 13 CLI paths, including false-done refusal, recovery,
  integrity, receipts, wrapper gate, and timeout. See candidate-smoke.json.
- Browser: receipt expansion, empty UNKNOWN, and no horizontal overflow at
  375/768/1440. Demo screenshot visually inspected at 1280x720.
- pip-audit 2.10.0 found no known vulnerabilities in the candidate environment,
  but skipped unpublished showwork 0.5.0 because PyPI could not identify it.
  The wheel declares no runtime dependencies. The public release must be
  scanned again after publication; this candidate result is not a package scan.
- Bandit findings were low severity only: subprocess imports/calls, fixed Git
  executable lookup, and false positives on the display token "OK". Subprocess
  call sites were reviewed; the timeout and reader-execution findings above
  were fixed. No embedded credential was found in those display literals.
- GitHub Dependabot alerts are disabled; code scanning has no analysis. Neither
  service is counted as a clean scan.
- Copilot and Bugbot skipped review due quotas. Their absence is recorded,
  not represented as approval. Owner explicitly authorized admin merges.

## Boundaries and remaining work

Snapshot coverage excludes generated directories, symlinks, files above 32 MiB,
and files beyond the 50,000-file cap. It detects changes to covered preexisting
files, not all possible damage or the correctness of every declared change.
A hash chain needs an externally anchored head to detect a rewritten or removed
suffix; it is not authentication against an actor who controls the entire tree.
The command checker runs trusted project Python scripts, not sandboxed code.
The process wrapper contains ordinary descendants; detached processes that
escape a process group are outside that guarantee. HTTP probes permit local
services by design and must be disabled for untrusted ledgers.
The supervisor overlay is filesystem-only; command/network/Git evidence is
unverified there. Frozen apps must supply a real Python interpreter.
Issue #70 is a downstream BMD application integration, not a shipped BMD change.

Sign-off: OpenAI | GPT-6 | auto
