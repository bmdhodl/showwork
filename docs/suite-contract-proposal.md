# Optional suite evidence references: owner review proposal

**Historical proposal.** The owner selected its offline example-only scope on
October 3, 2026. The implemented mapping, installed-package reproduction and BMD
handoff are now in [suite evidence references](suite-evidence.md). The proposal
below retains the original review state and source identities for provenance;
its former approval request is resolved. It grants no release, BMD installation,
new API, persisted join or fresh dispatch authority.

Prepared October 3, 2026 for [#102](https://github.com/bmdhodl/showwork/issues/102),
[#103](https://github.com/bmdhodl/showwork/issues/103) and
[#70](https://github.com/bmdhodl/showwork/issues/70). **Proposed, not approved or
implemented.** This document replaces neither product's contract.

Recommendation: approve one offline, example-only join using explicitly supplied
local references and existing fields. Keep the three observations separate. Add
no SDK API, persisted join record, service, dispatcher, dependency or BMD install.
The strongest counterargument is that even an example can become an accidental
public contract before an outside consumer has demonstrated the need.

The companion [AgentGuard #743](https://github.com/bmdhodl/agent47/issues/743)
requires: “Patrick approves any new public API, storage shape, trust boundary, or
cross-product contract before implementation.” Agreement is required before the
example code is written. Revisit after an owner decision or a concrete consumer
request; the existing October 13 decision remains separate.

## Reviewed interfaces

| Concern | Existing source | What it establishes | What it cannot establish |
| --- | --- | --- | --- |
| Selection and authorization | BMD's selected task and owner authorization | Which work is selected and which operation is permitted | Task correctness, another product's permissions |
| Runtime observation | AgentGuard `build_receipt`: trace filename/hash, event and call counts, recorded cost, warnings, stops and package version | What the supplied trace records | Provider invoice, authentic origin, complete interception, successful task |
| Decision observation | AgentGuard decision event: workflow/trace/object/actor IDs, event type, binding state, outcome | Recorded proposal, edit, override, approval or binding | Permission for a fresh dispatch |
| Declared acceptance | showwork spec-v0.5 requirements, scope/check definition, finish status/outcome/completion scope, command evidence | Result for declared checks at the recorded execution | Full requirement coverage, adequate tests, human usefulness |
| Integrity and freshness | showwork reader: integrity, spec coverage, manifest, freshness, recorded outcome, current execution/outcome | Whether bounded loaded evidence supports its recorded close | Current command execution, origin authentication, current revision discovery |
| Current BMD display | Existing `verified`, `claimed`, `failed`, `unknown` vault/frontmatter interpretation | Current BMD evidence display contract | A showwork runtime overlay; none is imported by the reviewed module |

Source identities inspected: AgentGuard main
`01ccdcf8a49992580f621679e90da5c9ef0b4e86` (SDK 1.4.1),
showwork main `472dfb0e1a9942b2559dd4c3e141b7eb5cae4b06`, and the reader
implementation reviewed in [PR #144](https://github.com/bmdhodl/showwork/pull/144).
The BMD owner checkout's inspected main revision was
`a30f10d67c372e6e8fd14f60898b4be31b016ece`; its canonical task owns implementation.
These are source reviews, not installed-package compatibility runs.

Public originals:
[AgentGuard receipt](https://github.com/bmdhodl/agent47/blob/01ccdcf8a49992580f621679e90da5c9ef0b4e86/sdk/agentguard/receipt.py),
[decision events](https://github.com/bmdhodl/agent47/blob/01ccdcf8a49992580f621679e90da5c9ef0b4e86/sdk/agentguard/decision.py),
[showwork specification](../SPEC.md), [reader capabilities](readers.md), and
[BMD boundary #744](https://github.com/bmdhodl/agent47/issues/744).

## Proposed reference-only example

The caller supplies a trusted workspace root, a showwork session and requirement
ID, a selected revision, and an AgentGuard trace file. These are ephemeral example
inputs, not a new persisted schema. Each source is opened independently. A path
must remain confined to the supplied root. The trace hash identifies those bytes;
it is not a signature. An explicit active gate may execute only when the caller
has authorized execution. The read-only display never invokes that gate.

The example displays the runtime observation beside the recorded acceptance and
the current execution status. A missing or mismatched link remains unknown even
if another row is green. No fallback silently substitutes vault evidence for a
missing showwork reference. A recalled approval or successful check never grants
another provider call.

| Example input | Runtime observation | Acceptance display | Current execution / action |
| --- | --- | --- | --- |
| No receipt or unreadable reference | Unknown | Unknown | Not performed; no dispatch |
| Prose only, no successful outcome close | Independently shown if present | Claimed / unverified | Not performed |
| No runtime stop, declared test failed | No recorded stop | Failed work | A budget result cannot hide failure |
| Budget exhausted, requirements unfinished | Stopped | Incomplete / unverified | No further call authorized |
| Budget exhausted, one artifact check passed | Stopped | That artifact observation only | Remaining work incomplete |
| Intact matching close, artifact scope | Independently shown | Recorded verified artifact scope | Not performed; behavior unverified |
| Intact matching close, behavior scope | Independently shown | Recorded verified declared behavior scope | Not performed until an explicit active gate |
| Reopened or changed manifest | Independently shown | Recorded outcome unverified | No current success inferred |
| Wrong workspace/revision/version or required unknown semantics | Independently shown | Unknown / incompatible | No fallback to green |
| Corrected retry | New attempt shown separately | New result shown beside original failure | Original evidence retained |

Existing Python and JavaScript readers interpret the same ten frozen fixtures.
They preserve append order through clock rollback, reject tampering and missing
or incompatible evidence, and keep `current_execution: not performed`. This
shows two reader implementations, not AgentGuard/BMD interoperability or adoption.
Run `python scripts/check_reader_conformance.py` after the reader branch lands.

After approval, installed pinned packages must exercise the stopped/failed,
corrected/verified, missing, stale, wrong-root and wrong-revision cases. Capture
pre-dispatch denial separately from acceptance execution. The fixture must prove
neither package requires the other. Until then those acceptance boxes remain open.

## BMD handoff conflict and proposed documentation correction

The older [BMD example](../examples/bmd/README.md) and
[September request](requests/bmd-overlay-receipts.md) prescribe showwork 0.5.0,
vendoring a module, an automatic overlay/fallback and BMD installation. Those
instructions predate the selected roadmap and are historical, not execution
authority. Do not copy them into a new vault request or implement their commands.

After owner approval, replace the obsolete installation recipe with the reviewed
reader capabilities, compatibility matrix and reference-only mapping above.
The existing BMD task then owns any UI, packaging or dispatch change, with real
Playwright acceptance on the designated test host. This showwork card adds no
ledger or dependency to bmd-desktop and migrates no vault claims.

Raw claims, command output and sensitive source content stay in the user's
workspace. Sharing is an explicit, redacted summary with references. Integrity,
process exit, check success, human acceptance and promotion eligibility remain
separate observations. No combined success badge is proposed.

## Owner choices

1. Approve the offline example-only join and documentation replacement above.
   This permits pinned-package fixtures without creating a persisted contract.
2. Keep products independent and retain this proposal until a named consumer
   requests interoperability. This avoids support obligations but leaves the
   existing handoff work open.
3. Request a public API or persisted join design. This needs a separate schema,
   compatibility and trust review before implementation.

Recommendation: option 1. No option authorizes release, BMD production changes,
provider spending or publication of private execution content.

Sign-off: OpenAI | GPT-6 | auto.
