# Declared acceptance in CI summaries

Issue: [SW-08 #93](https://github.com/bmdhodl/showwork/issues/93).
Prepared from main `852fb59ebce0deb2abbfde40814fb985a28a57b9` on October 2, 2026.

The existing action displayed only the gate verdict and refusal text. Its summary
now shows each selected session, the declared requirement and scope, its current
result, the committed receipt, and command evidence with observed revision,
exit code and stdout hash. Disabled or absent execution stays visible. Historical
integrity and the gate's actual verdict remain separate from advisory job policy.

The formatter consumes the result from the one existing gate invocation. It does
not execute record contents or run a second verification. The ledger format and
JSON gate output are unchanged. Command and network execution remain disabled by
default; no workflow or repository permission was changed.

The regression failed before implementation because the coverage formatter was
absent. The final focused run passed 54 tests, including the actual CLI's
multi-session route, disabled/missing requirements, malformed input, unsafe URLs,
Markdown/HTML injection, redaction, and existing action/refusal/legacy selection
cases. The full Python suite passed 649 tests in 418.93 seconds on Windows,
Python 3.13.2. [Raw full-suite output](ci-acceptance-summary-20261002/full-suite.txt)
is retained. The source receipt reruns the full suite with the same 600-second
command budget already used by this repository's CI and nightly suites.

The new summary requires an action pin containing this change. The published
0.6.5 action keeps its prior text summary until a consumer deliberately updates
its pin. No package release or branch-protection change is included. Declared
checks do not establish requirement completeness or test adequacy.

Receipt session: `codex-ci-summary-01a1000f`.
Sign-off: OpenAI | GPT-6 | auto.
