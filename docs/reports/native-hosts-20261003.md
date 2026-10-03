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

The full actual-host acceptance runs, two independent task slugs and supported
Cursor-host proof remain outstanding. These issues stay open. A synthetic payload,
READY response, installed version or observer dispatch is not pilot activation.

Receipt: `codex-native-hosts-01a1000f`.

The full Python suite passed 678 tests. The first strict finish correctly refused
because this task's configured temporary directory did not exist; Node's temporary
fixture creation failed. Creating that task directory repairs the test harness,
without changing source, skipping a check or weakening the receipt. The refusal
remains in the append-only session history.
Sign-off: OpenAI | GPT-6 | auto.
