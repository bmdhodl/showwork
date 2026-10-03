# Roadmap evidence readout, October 3, 2026

Prepared for [#89](https://github.com/bmdhodl/showwork/issues/89),
[#92](https://github.com/bmdhodl/showwork/issues/92),
[#107](https://github.com/bmdhodl/showwork/issues/107),
[#108](https://github.com/bmdhodl/showwork/issues/108),
[#109](https://github.com/bmdhodl/showwork/issues/109) and
[#111](https://github.com/bmdhodl/showwork/issues/111). This is a dated preparation
packet, not the October 13 owner verdict or the planned December retention window.

## Observed adoption and denominators

The inspected sources are the existing September 21 pilot readout, all 44 public
issues excluding pull requests and their 16 comments captured October 3, the live
pilot issue (no comments at refresh), and the original outside contribution
[PR #143](https://github.com/bmdhodl/showwork/pull/143). This describes reports
available in those sources; unreported use and private feedback are unknown.

| Observation | Inspected-source count / denominator | Interpretation |
| --- | --- | --- |
| Qualifying outside pilot activation | 0 verified reports; target 3 | No actual cohort denominator is available |
| Same outside project, second real task at least seven days later | 0 verified reports; target 2 | Retention rate cannot be calculated |
| Outside installed bug report and clean-environment retest | 1 linked issue, [#64](https://github.com/bmdhodl/showwork/issues/64) | Inbound support evidence; not pilot activation |
| Outside accepted code contribution | 1 original merged PR, #143 | Contribution; not a completed task/refusal/repeat receipt |
| Internal dogfood | Retained source/CI receipts | Excluded from outside activation; no cohort aggregate computed |
| Bots, mirrors and unknown-origin installs | Excluded / unmeasured | No download count used as a participant denominator |
| Stars / forks at live refresh | 0 / 2 | Discovery signals; forks are not verified integrations |

Sources are deduplicated by the linked issue or PR identity, not comment count.
#64 was created August 26 and closed September 13; it is historical inbound, not
an activation inside the September 21–October 3 observation interval. PR #143 was
merged October 3 and is a distinct contribution. Their identities are retained
locally for deduplication; this report publishes only counts and source links.

Successful/attempted outside setups, review minutes, first-value time, manual
interventions, false refusals, true failures caught during customer work, setup
abandonment and maintainer support minutes are **unmeasured**. A missing report is
not zero effort or zero false refusals. Authored regression controls and internal
strict-finish refusals are test evidence, not customer outcomes or saved time.

The next measurable bottleneck is qualifying outside task evidence: a permitted
real task, retained intentional refusal/repair, and a repeat at least seven days
later. Installation/support friction has one historical reproducer. The current
sources do not establish whether installation, adequacy or handoff causes most
abandonment. Keep the existing inbound pilot path; no cold outreach or telemetry
database is proposed.

## Competitive replay

The original eight SW-02 cases and expected outcomes were replayed without corpus
additions or deletions. Source showwork main was
`472dfb0e1a9942b2559dd4c3e141b7eb5cae4b06` with package metadata 0.6.5; this is a
source run, not proof that the published 0.6.5 wheel contains today's fixes.
Windows 11, Python 3.13.2, pytest 8.4.2, Node 22.14.0. Agent Verify 1.2.0 at
`b0212fd5c863f620e013f821d8234842adb8e8e3` is its current default-branch source,
unchanged from the previous comparison. All eight expected showwork observations
matched. Total fixture wall time was 15,885 ms, not setup or human review time.

| Frozen case | Plain pytest | showwork observation | Agent Verify supplied-message check |
| --- | --- | --- | --- |
| Honest pass | Pass | Artifact-scope close passes | Pass |
| Honest failure | Fail | Missing-artifact close refused | Refuses false test-pass message |
| Test never run / handwritten summary | Actual test fails | Artifact text can pass; declared test execution refuses | Reruns tests and refuses |
| Weak mocked fixture | Pass, production result still wrong | Declared weak test passes | Pass |
| Undeclared deletion | Pass | Refuses baseline file damage | Pass for “All tests pass” |
| Stale referenced content | Pass | Fresh reference passes, changed content fails | Pass for test-only message |
| Missing receipt | Pass | Outcome close refused | New test check passes |
| Cross-client fixture | Pass | Second verifier reads existing per-session evidence | Test message passes; writes its own receipt |

These workflows declare different checks. A test-only pass is not a promise that
the tool checked an undeclared file or supplied a historical receipt. There is no
general detection-rate or superiority claim. In particular, no tool in this
comparison detects the omitted production behavior behind the mocked fixture.

PatchCase 0.1.0 at `ac1ce09ecbed1b1428b556251cf907b9bdf5102d` was run against four
of the unchanged seeds with an explicit pytest-pass manifest. It returned
`verified` for honest pass, weak fixture and undeclared deletion, and `falsified`
for the failing test. The weak fixture's separate production probe printed 5.
The first adapter expected the wrong display word `failed`; that run and the
correction to the source enum `falsified` are retained. No case or outcome was
changed to improve a score. These four exploratory mappings are reported apart
from the frozen eight-case replay; the other PatchCase cases remain untested.

| Alternative | Current checked source | Execution evidence / limit |
| --- | --- | --- |
| Native hooks plus CI | Host recipes and existing CI | Claude observer dispatch proved; full host task/repair runs incomplete; Codex policy and Cursor availability limits retained |
| [Agent Verify](https://github.com/Orthogon-AI-Labs/agent-verify) | Current 1.2.0 commit above | Eight supplied-message cases measured; actual host plugin workflow untested |
| [Agent Receipts](https://github.com/inchwormz/agent-receipts) | 0.2.0, `3bc5f285c9d0e96857e92cc4c95e1f5d531cec75` | Source inspected; Rust engine execution untested because cargo/rustc are absent |
| [PatchCase](https://github.com/joemagicstr8zzz/patchcase) | 0.1.0 commit above | Four source-run manifest cases measured; actual Codex skill workflow untested |
| [Microsoft AGT limitations](https://github.com/microsoft/agent-governance-toolkit/blob/main/docs/LIMITATIONS.md) | Current official limitations and draft evidence specification | Documentation review only; no outcome-verification implementation benchmarked |

Raw results and the optional PatchCase reproduction are in
[`roadmap-readout-20261003/`](roadmap-readout-20261003/).
Repeat the frozen comparison with a reviewed Agent Verify checkout:

```text
SW02_AGENT_VERIFY=<reviewed-checkout>
python examples/sw-02-bench/run.py --out <outside-workspace>/results.json
python docs/reports/roadmap-readout-20261003/reproduce-patchcase.py --patchcase-checkout <reviewed-patchcase-checkout> --out <outside-workspace>/patchcase.json
```

No second independent MCP/export/anchor blocker was found in the inspected public
reports. The completed demand investigation therefore retains CLI/SDK use and
defers those speculative expansions. Plain CI or Agent Verify suffices for the
test-message slice; use it where that is the selected job. The observed showwork
slice to preserve is explicit requirement scope, current rerun and undeclared
baseline damage. Do not add a hosted judge or signing service in response to a
competitor README.

## Next-cycle preparation and remaining gates

Recommendation, pending the October 13 owner decision: retain pre-1.0 and MIT,
independent local use and one visible outcome per selected release. Rank the next
outcomes as (1) usable host setup with actual task evidence, (2) acceptance-review
counterexamples, (3) reviewed reference-only interoperability when a consumer
needs it. Reader freshness and CLI interpreter/diagnostic defects have concrete
regressions; these take precedence over speculative transport or provenance.

No promotion threshold is proved: 100 stars, three independent integrations or
ten nontrivial stranger issues are not shown by this inventory. The demotion
predicate's zero-inbound term is contradicted by the outside bug/contribution.
This does not select promote, maintain or demote early. #92 remains an October 13
owner decision. No v1 jump, paid hosting, auto-publication or release date is chosen.

Compatibility policy proposal: keep historical reading fields explicit; mark
unknown mandatory semantics incompatible; preserve recorded failures/retries;
document any changed executing capability. A new ledger shape or authority
contract still needs owner approval. There is no promise that a read-only view
executes a command or establishes adequate requirements.

For #111, the existing authored 20-development/40-holdout proof-checker cases are
not independently labeled real failures. No permitted independent cohort has
been supplied for this evaluation. Abstention, false support, useful recognition,
real-case latency and cost remain unmeasured. No provider endpoint was called and
no deterministic verdict was changed. Resume only with explicit case submission,
independent labels frozen before runs, disclosure and the existing workflow's
cost cap. The authored corpus does not justify a general accuracy claim.

This packet completes current-source investigation and preparation. Pilot targets,
actual supported-host tasks, the dated owner verdict, installed-artifact suite
join and release/campaign activation remain open, each on its existing issue.

The first full-suite gate after integrating the acceptance example refused
because its new shell omitted the existing task/CI 600-second command setting
and used the 120-second default. The refusal is retained. The rerun restores
`SHOWWORK_COMMAND_TIMEOUT_SECONDS=600`; no product default or check was changed.

Sign-off: OpenAI | GPT-6 | auto.
