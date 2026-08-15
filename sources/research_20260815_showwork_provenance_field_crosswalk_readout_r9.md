# showwork provenance field crosswalk readout r9

Date: 2026-08-15  
Scope: internal vocabulary comparison with selected W3C PROV concepts. This
does not serialize showwork as PROV, add RDF, change the ledger schema, or
claim standards conformance or independent attestation.

## Result

Current showwork receipts have useful analogies to entities, activities,
agents, time, and derivation, but most relations are approximate and several
important responsibility and revision relations are absent. Use PROV as an
explanation aid only. Do not describe the current pack as a PROV graph.

The [W3C PROV primer](https://www.w3.org/TR/prov-primer/) describes provenance
in terms of entities, activities, agents, responsibility, and time. The
[W3C PROV-O recommendation](https://www.w3.org/TR/prov-o/) supplies concepts
such as `prov:Entity`, `prov:Activity`, `prov:Agent`, generation, derivation,
attribution, association, revision, and invalidation. The crosswalk below is
an interpretation of current fields, not a conformance assessment.

## Crosswalk

| Current showwork field/evidence | Related PROV concept | Mapping | Boundary |
|---|---|---|---|
| Session record and session events | `prov:Activity` | Approximate | A session is execution evidence, not a typed PROV activity with a declared usage graph. |
| Claim text and claim record | `prov:Entity` | Approximate | The claim is a recorded assertion; its domain entity and generation semantics are not declared. |
| Command receipt and evidence-pack file | `prov:Entity` | Approximate | The file is an artifact, but the pack does not assert a PROV entity identity or complete derivation. |
| `agent` label on session start | `prov:Agent` | Approximate | `codex`, `claude-code`, or another label identifies a reported actor class, not a verified person or service identity. |
| `ts` timestamp | PROV time | Approximate/direct data | The timestamp is retained, but the exact event semantics and clock provenance are not independently established. |
| `prev` hash chain and audit heads | Derivation/order analogies | Approximate | Hash linkage supports ledger integrity and ordering; it is not automatically `prov:wasDerivedFrom`. |
| `check`, result, and verifier output | Generation/activity result | Approximate | They describe verification behavior but do not establish a separate provenance activity graph. |
| Fork count and heads | Alternate/specialization analogies | Approximate | A fork is an integrity condition; resolution and specialization relations are not declared in PROV terms. |
| Retraction state | `prov:Invalidation` analogy | Approximate | Retraction can mark a claim as no longer relied on, but the current pack may omit the originating claim relation. |
| Bypass marker | Association/responsibility analogy | Absent | A bypass flag does not prove who accepted risk or under what authority. |
| Source revision/commit | Entity revision | Absent in historical command receipts | The command receipt does not bind its output to a source revision. |
| CWD, environment, dependency lock, fixture path | `prov:used` / usage context | Absent in historical command receipts | The execution inputs needed for replay are not fully recorded. |
| Human reviewer, authorization, or attestation | `prov:Agent` responsibility/association | Absent | Agent labels and local ownership do not prove human review or independent attestation. |

## Answer boundary

The crosswalk supports plain-language answers such as “this receipt records a
verification activity at this timestamp” and “these lines are linked by the
ledger hash chain.” It does not support “this is a PROV-compliant graph,”
“this output is independently attested,” “a named human approved it,” or “the
execution is fully reproducible.”

Evidence paths:

- `K:\showwork\sources\research_20260815_showwork_scope_state_answer_contract_r8.md`
- `K:\showwork\sources\research_20260815_showwork_receipt_compatibility_evidence_matrix_r8.md`
- `K:\showwork\.showwork\claims-2026-08-15.jsonl`
- `K:\showwork\.showwork\sessions.jsonl`
- `C:\Users\patri\Documents\Obsidian Vault\Reports\Research\showwork-scope-state-answer-contract-2026-08-15.md`

## Decision

KEEP the crosswalk as internal explanatory documentation. NO CHANGE to the
schema, verifier, pack, public copy, compliance position, or release process.
Vocabulary alignment is not standards conformance, legal compliance, human
authority, or adoption evidence.
