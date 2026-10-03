# Demand-gate investigation, October 3, 2026

Issues: [#100](https://github.com/bmdhodl/showwork/issues/100),
[#101](https://github.com/bmdhodl/showwork/issues/101),
[#110](https://github.com/bmdhodl/showwork/issues/110), and
[#112](https://github.com/bmdhodl/showwork/issues/112).
Source reviewed: main `852fb59ebce0deb2abbfde40814fb985a28a57b9`.

Decision: use the existing CLI and receipt documentation. Select no MCP adapter,
standard export or signing service. The cards explicitly allow a no-build result
when their demand gate is unmet. This closes the investigation and cancels the
conditional implementation, rather than representing an unbuilt feature as
delivered. Reopen when a qualifying consumer supplies the evidence below.

## Observed demand

The public open/closed issue inventory was read on October 3 and is retained in
[public-issues.json](demand-gates-20261003/public-issues.json). The committed
[pilot readout](sw-04-pilot/README.md) records 0 qualifying activations and 0
qualifying repeat users. No new qualifying participant or shell-blocker report
was found in that issue inventory. This is a count of verified reports in these
sources, not a claim to have inspected private communications or all usage.

[Issue #64](https://github.com/bmdhodl/showwork/issues/64), by an outside maintainer,
is a genuine undeclared-damage report. It does not request an MCP interface,
standard export or authenticated receipt provenance. Owner-authored planning,
bot cards and permission tests do not establish independent consumer demand.

| Gate | Verified evidence in these sources | Result and concrete resume condition |
| --- | --- | --- |
| MCP: two pilot users identify shell integration as a blocker | 0 qualifying reports | Documentation sufficient; reopen #100 with two independent reports |
| MCP implementation: an approved adapter from #100 | None selected | Cancel #101's conditional build; no two-client or protocol proof is claimed |
| Standard export: two independent requests or one working outside integration | 0 qualifying requests; no verified working integration | No-build #110; select at most one format when its named consumer exists |
| Anchoring: a real consumer needs authenticated provenance | No named qualifying consumer or verifier workflow | Defer #112; reopen with the consumer, attacker, expected identity and retained trust root |

## MCP comparison and boundary

The current CLI already returns structured receipt JSON; the process-free reader
work in #96 improves its read boundary independently of MCP. A future interface
could expose list-session, inspect-requirement and explain-result operations over
the same records, with a workspace chosen by the caller, bounded input/output,
and unknown results for missing, malformed, unsupported or escaping evidence.
Its result must retain integrity, scope, freshness, requirement inventory and
limitations. Imported text and paths cannot authorize execution. An explicit
trusted verification operation would be separately selected and reviewed.

| Option | Cost and trust implication | Selection |
| --- | --- | --- |
| Existing CLI / local Python reader | Existing package and workspace access; caller explicitly chooses any execution | Keep |
| Optional MCP extra using an established SDK | Protocol and dependency maintenance; a selected client and workspace confinement need proof | No demand to select it |
| Existing host's adapter | Reuses a host but inherits its data-access and trust configuration; two client implementers still need to validate it | No named implementers |

No protocol version, dependency extra, listener, authentication system or client
configuration is activated. The [MCP tools specification](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
provides structured output and warns clients not to treat tool annotations as
trusted authority. Naming a read-only operation alone would not enforce that
boundary. No protocol implementation or two-client smoke test was run.

## Export comparison

Existing `scripts/evidence_pack.py`, `showwork report --json` and receipt JSON
consume the current records. They do not create authenticated execution or
establish test adequacy. The existing evidence pack also includes authored
framework commentary; it should not be relabeled as a universal proof format.

| Format | Natural consumer | Missing fit for this investigation |
| --- | --- | --- |
| JUnit | A test-results viewer | A named viewer and explicit mapping for missing/unknown, artifact scope and receipt identity |
| SARIF | A finding-oriented review client | A named client and lossless semantics for observations versus acceptance |
| OpenTelemetry | An existing runtime/event consumer | A named consumer; no tracing backend or new current-state store is selected |
| AGT evidence pointer | A selected policy dispatcher/auditor | A concrete integration and explicit subject, identity and verification pointer contract |

The [AGT evidence draft](https://github.com/microsoft/agent-governance-toolkit/blob/main/policy-engine/spec/agt/AGT-EVIDENCE-1.0.md)
is version 1.0.0-alpha and maps bounded artifact references and verification
pointers to policy decisions. That draft is not evidence of a showwork consumer.
There is no selected format, so no consumer round-trip or compatibility result is
claimed. Any later mapping must preserve failed/unknown/legacy states, scope,
missingness and source identity through a real consumer's round-trip.

## Anchoring comparison

Internal hash-chain integrity detects edits that break a retained chain; an
attacker controlling the whole unanchored file can replace it and recompute the
chain. A retained independent hash can detect replacement if the reviewer knows
which subject and revision it names. It does not authenticate an author or prove
that a test was adequate. A wrong subject must fail the comparison.

[GitHub artifact attestations](https://docs.github.com/en/actions/concepts/security/artifact-attestations)
use Sigstore to bind build provenance to source and workflow identity. Verification
and an expected identity policy are necessary; an attestation does not establish
software security or application acceptance. An actual consuming workflow would
need correct-subject and wrong-key/identity failure fixtures before adoption.

No consumer or retained identity policy is selected here. No signing keys,
workflow change, external attestation, replaced-chain fixture or online/offline
verification success is claimed. The card explicitly permits deferral when no
consumer needs the property. Existing chain and reference documentation suffice
until that demand exists; no custom cryptography or core dependency is added.

## Limits and revisit

The strongest counterargument is that easier integration might help attract the
first user. The explicit demand gates avoid selecting several unvalidated
interfaces before learning which one a real maintainer cannot do without.
This is reversible: retain these cards and reopen on the concrete conditions
above. The October 13 owner decision in #92 and pilot completion in #89 remain
open; this investigation supplies no adoption or promotion verdict.

Receipt session: `codex-demand-gates-01a1000f`.
Sign-off: OpenAI | GPT-6 | auto.
