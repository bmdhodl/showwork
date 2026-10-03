# Native host recipe validation, October 3, 2026

Issues [#97](https://github.com/bmdhodl/showwork/issues/97),
[#98](https://github.com/bmdhodl/showwork/issues/98) and
[#99](https://github.com/bmdhodl/showwork/issues/99).

The project recipes provide a Codex skill, native hook templates, no-write preview,
configuration-preserving installation and removal of unchanged generated content.
The new native Stop command emits host-valid JSON, accepts bounded payload input,
and reads existing receipts without execution, network requests or ledger writes.
Explicit finish and the committed gate remain the acceptance boundaries.

The first five setup/protocol regressions failed because these features did not
exist. The combined host/setup/reader focused suite subsequently passed 32 tests.
The installed Codex skill passed the skill validator. This is protocol and recipe
verification, not proof that three agent hosts completed real tasks.

| Actual host probe | Observed result | Remaining limitation |
| --- | --- | --- |
| Codex CLI 0.154.0, ephemeral, read-only, existing ChatGPT authentication | Discovered the project skill and attempted to read it; shell execution was rejected with “blocked by policy” | Skill body could not be read; no full task or Stop dispatch proved; no hook-trust bypass used |
| Claude Code 2.1.238, print mode, session persistence off | Replied READY and dispatched the project native Stop command; its stderr reported matching artifact-scope close and `current_execution: not performed` | This probe did not make the host perform the full lying-claim/repair task |
| Cursor 3.22.7, Windows x64 | Installed desktop launcher version read back | Headless agent path and native desktop automation unavailable; actual recipe activation untested |

The Claude dispatch probe used a temporary stderr wrapper around the generated
command so dispatch could be observed without adding a writer. The isolated repeat
used an empty strict MCP configuration, no agent tools and process-local auto-memory
disablement as documented in the [official environment reference](https://code.claude.com/docs/en/env-vars).
No account setting, trust entry or global configuration was changed. Raw host logs
remain local because they include host metadata; this report publishes observations
and limitations rather than that metadata or account information.

Uninstall readback removed the unchanged Codex generated hook and skill while
retaining unrelated `.git`. The deliberately edited Claude test wrapper stayed
in place, and all receipt bytes remained unchanged. Unit fixtures additionally
cover repeated installation, foreign hooks, malformed input, oversized input,
edited skill retention, unbound IDs and all three JSON response protocols.

## Claude behavior lifecycle smoke

Two independent task slugs subsequently exercised a real broken `add(2,2)`
production probe. The test driver declared behavior before its claim; explicit
finish returned 2 for the broken implementation. An actual Claude print session
then stopped normally with exit 0 and dispatched native Stop, which read the
recorded result as UNVERIFIED without executing the probe or changing receipts.
The driver repaired the production function, the same explicit check returned
0, and a second actual Claude Stop read recorded VERIFIED behavior while retaining
`current_execution: not performed`. Both tasks repeated that failure/repair path.

The driver authored the toy source and repair. Claude performed the conversational
Stop lifecycle only. This is not host-authored task completion or customer
activation. The four host calls took 2.740–3.337 seconds each; added hook overhead,
real-use noise and human review effort were not isolated or measured.

An additional actual Claude smoke dispatched a deliberately missing Python
launcher. The host still stopped with exit 0 and emitted a missing-command
diagnostic; no native observer or acceptance ran. Malformed/oversized payload,
Stop reentry and byte-preservation fixtures cover the observer itself.

After removing each temporary observation wrapper, generated-hook uninstall
restored the prior foreign project configuration and preserved every receipt
byte. [Sanitized behavior results](native-hosts-20261003/claude-behavior-smoke-results.json)
and [missing-runtime result](native-hosts-20261003/claude-missing-runtime-result.json)
are retained. Private host logs stay local.

This completes the Claude observe-only lifecycle boundary for #98. Codex's real
refusal/repair/interruption/handoff and Cursor's full supported-host task remain
outstanding on #97/#99. A READY response, installed version or observer dispatch
is not pilot activation.

Receipt: `codex-native-hosts-01a1000f`.

The initial full Python suite passed 678 tests. The first strict finish correctly refused
because this task's configured temporary directory did not exist; Node's temporary
fixture creation failed. Creating that task directory repairs the test harness,
without changing source, skipping a check or weakening the receipt. The refusal
remains in the append-only session history.

PR review found that uninstall could delete a pre-existing empty host config
without ever installing a generated hook. Six regression cases failed before
the repair: Claude, Codex and Cursor, each with preview and removal. Uninstall
now leaves the exact original bytes untouched when it removes no generated entry.
All 16 host-recipe tests passed after the repair. The [failing controls](native-hosts-20261003/uninstall-empty-before.txt)
and [passing host suite](native-hosts-20261003/uninstall-empty-after.txt) are retained.
The final strict finish and tracked gate rerun the full integrated Python suite
and JavaScript conformance rather than relying on the initial 678-test count.
The first integrated rerun refused when the new shell omitted the task's existing
`SHOWWORK_COMMAND_TIMEOUT_SECONDS=600` setting and fell back to 120 seconds.
The full suite takes longer than that. The rerun restores the same setting used
by the earlier task gates and repository CI; it does not change a product default
or skip tests. This refusal also remains in the session history.
Sign-off: OpenAI | GPT-6 | auto.
