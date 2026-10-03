# CLI diagnostics and setup regressions

Issues: [#136](https://github.com/bmdhodl/showwork/issues/136),
[#137](https://github.com/bmdhodl/showwork/issues/137),
[#139](https://github.com/bmdhodl/showwork/issues/139),
[#140](https://github.com/bmdhodl/showwork/issues/140).
Base: main `852fb59ebce0deb2abbfde40814fb985a28a57b9`.

`--version` now prints the actual package version before workspace discovery.
A missing subcommand after options is named COMMAND; invoking with no arguments
retains the existing help view.

The locked command runner still uses showwork's interpreter. Execution evidence
now records the actual interpreter and resolved script in the existing `argv`
field; the claim retains the declared arguments. The specification and behavior
quickstart explain how to run showwork with a project's dependencies. No arbitrary
binary or new interpreter policy is enabled.

Failed commands include the actual Python version and a bounded six-line stderr
tail, falling back to stdout. Known secret forms, paths and terminal controls are
redacted. Exit codes, stdout/stderr hashes and the failure verdict remain separate
from diagnostic text.

`init` inspects actual command hook entries and recognizes both `showwork` and
`showwork.cli` module spellings. Following the Claude guide then initializing
twice preserves one showwork hook and the user's other hooks and permission data.

Before implementation, six of seven new regression cases failed. The fixes passed
the seven cases, and the full Python suite passed 647 tests on Windows, Python
3.13.2, in 460.42 seconds. The initial focused suite also covered 162 passing
existing cases; its remaining regression assertion was corrected to exercise a
missing subcommand after options, since an empty invocation intentionally prints
help. [Raw full-suite output](cli-diagnostics-20261003/full-suite.txt) is retained.

These changes require a source commit containing them. The published 0.6.5 package
is unchanged. #138's persisted snapshot exclusions await the owner's decision;
no exclusion or new-file coverage change is included.

Review follow-up: diagnostic redaction covers arbitrary absolute POSIX roots and
quoted paths, including interpreter context, instead of relying on a directory
allowlist. Hook detection requires a supported Python launcher; echoing module
arguments does not count as an installed hook. Both issues reproduced as failing
regressions before repair. The independently contributed #143 version fix and
its tests are retained, including the `-V` alias, rather than replaced by this
branch's overlapping implementation.

Receipt session: `codex-cli-defects-01a1000f`.
Sign-off: OpenAI | GPT-6 | auto.
