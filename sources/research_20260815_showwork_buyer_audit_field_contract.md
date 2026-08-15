# showwork buyer audit-field contract

Date: 2026-08-15
Scope: read-only field coverage research. No schema, public-copy, legal,
signing, release, or adoption change.

## Result

KEEP the current receipt surfaces and keep the buyer answer narrow. The
ledger has useful evidence for outcome verification and byte-level integrity.
It has partial coverage for action, agent identity, policy context, and
retention. It has no receipt-native proof of a human reviewer, authorization,
delegation, data lineage, or independent attestation. This is a field contract,
not a compliance assessment.

## Evidence inspected

- `python -m showwork.cli audit --json` on 2026-08-15: overall `YELLOW` because
  the earliest legacy files are pre-chain; 374 records, 342 chained, and 43
  accepted forks. The current `claims-2026-08-15.jsonl` file was `GREEN`,
  79/79 chained, with one fork across two heads.
- `scripts/evidence_pack.py`: date-bounded chain audit, session and claim
  counts, refusal and bypass counts, control mapping, and receipt inventory.
- `showwork` lifecycle records: `session.start` carries a session id, free-form
  `agent`, timestamp, and optional note. `session.finish` carries status,
  claims verdict, optional note, and an explicit `verify_bypassed` stamp.
- Claim records: session, timestamp, free-form claim text, severity, check
  type and arguments, plus the previous-record hash.
- [README.md](../README.md) and [compliance evidence-pack docs](../docs/compliance.md).

## Field matrix

| Buyer or governance field | Current observed surface | Classification | Safe inference | Still unknown or absent |
|---|---|---|---|---|
| Outcome | Claim text, deterministic check result, point-in-time finish verdict, and current export result | Partial | A stated repository outcome can be checked at assertion and rechecked at export | Business outcome, model quality, downstream effect, and why the outcome mattered |
| Action | Check type and check arguments, for example `file_exists`, `file_contains`, `path_moved`, or `command` | Partial | The receipt says what deterministic predicate was tested | A normalized action event, complete tool trace, input/output values, or actions outside the check |
| Agent identity | `session.start.agent` plus session id and timestamp | Partial | The receipt names the string supplied by the operator or adapter | Human identity, organization, model version, parent agent, authenticated principal, or proof that the named agent wrote the record |
| Policy context | Framework/control prose in an evidence pack and claim severity | Partial | A reader can see the selected export framing and red/yellow claim state | The runtime rule evaluated, policy version, decision input, authorization, or override reason |
| Retention | Append-only JSONL files, date-bounded export, and per-record chain | Partial | The exported bytes were chained when written and the stated range was retained locally | Retention schedule, deletion controls, backup coverage, access control, or a framework-specific retention determination |
| Integrity | `showwork audit` verdict, per-file heads, fork count, and evidence-pack refusal on a RED ledger | Supported for ledger integrity | A reader can detect changed, deleted, reordered, or unchained records within the audited ledger | Authorship, external timestamping, signer identity, hardware provenance, or truth of the underlying external world |
| Human review or authority | No dedicated field. A note or claim may mention a person, but it is free text | Absent | Nothing in the current receipt proves a human reviewed, authorized, delegated, or approved the action | Reviewer identity, role, time, decision, competence, delegation, escalation, and independent confirmation |
| Data lineage and sensitivity | Check paths and claim text may expose values unless the evidence pack is redacted | Partial | A reader sees what the existing check records and what the export renderer masks | Data classification, lawful basis, access authorization, input lineage, or complete privacy controls |
| Independent attestation | No signer, witness, or second verifier in the current surface | Absent | The local verifier rechecks its own deterministic claims | Independent party, signing key, hardware root, or external witness |

## Governance source boundary

The current consolidated [EU AI Act text](https://eur-lex.europa.eu/eli/reg/2024/1689/oj)
is scope-specific. Article 12 says high-risk AI systems must technically allow
automatic event recording and identifies traceability purposes. Article 19
addresses provider retention of automatically generated logs under the
provider's control, while Article 26(6) addresses deployer retention under the
deployer's control. Those provisions do not turn this repository's receipt
format into a legal compliance result.

The [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework) is
intended for voluntary use and is a broad risk-management framework. It is not
a field-level acceptance test for this ledger.

## Decision

NO CHANGE. Use this matrix to answer buyer questions honestly. A future schema
or adapter would require a separate owner-gated demand signal and a new
contract; this research does not justify one.
