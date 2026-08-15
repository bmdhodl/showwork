# showwork provenance wording drift audit r10

Date: 2026-08-15  
Scope: read-only inspection of README, SPEC, docs, examples, current source
reports, and queue copy. No wording was edited and nothing was published.

## Result

The repository mostly states bounded deterministic verification, but several
phrases require their existing qualifiers to remain attached. The safe line is
“showwork verifies recorded local predicates and ledger integrity.” The unsafe
drift would be to turn that into PROV conformance, authenticated authorship,
legal compliance, independent attestation, human approval, full replay, or
adoption.

## Wording inventory

| Evidence | Classification | Read-only finding |
|---|---|---|
| `README.md:8`, `23-26`; `SPEC.md:56-59` | Supported with local scope | Falsifiable claims, deterministic checks, refused closes, retractions, and append-only records are supported by the current implementation/tests. “Against reality” means the declared local check, not the whole external world. |
| `README.md:95-118`; `SPEC.md:194-269`; `docs/concurrency.md:46-84` | Supported with policy qualifier | Hash-chain tamper evidence, fork counting, heads, ordinary fork-tolerant GREEN, and strict fork RED are explicitly specified. This proves ledger integrity behavior, not branch authority or authorship. |
| `README.md:19`, `163-165`; `docs/compliance.md:3-11`, `28-43`; `docs/evidence-pack-sample.md:5` | Qualified, keep disclaimer adjacent | Framework control mappings are supporting evidence only. The docs explicitly say not legal advice, not certification, and not sufficient by themselves. Moving the mapping without the disclaimer would create overclaim risk. |
| `README.md:155-159`; `docs/false-done-rate.md:36-37` | Qualified metric | The false-done rate is a bounded named corpus/methodology, not a universal reliability rate. Keep its population and caveats attached. |
| `README.md:180-193` | Qualified case-study/provenance story | The heading is narrative provenance and the sanitized snapshot is a bounded aggregate with RED/failure visibility. It is not W3C PROV conformance or externally authenticated provenance. |
| `README.md:197`, `202`, `204` | Qualified external context | The cited survey is context, not endorsement; the text already says so. Do not turn it into adoption or validation evidence. |
| `README.md:208-210` | Supported only as bounded product distinction | “Not observability,” “runtime outcome checks,” and deterministic checks are supported. “Audit-grade” must not be read as a certification or framework result. |
| `README.md:218` | Future/owner-gated | Detached signing is a roadmap item, not a current capability. No current receipt supports signing or external timestamp anchoring. |
| `docs/fleet-adoption.md:1-6`, `67-74` | Hypothetical procedure, not adoption proof | “Adopting ... across a fleet” describes a rollout pattern. It does not establish customer adoption; harvest language must remain tied to actual evidence. |
| `sources/research_20260815_showwork_provenance_field_crosswalk_readout_r9.md:12-18`, `24-38` | Internal explanatory only | PROV mappings are explicitly approximate/absent. They do not create a PROV graph, authenticated responsibility, or standards conformance. |
| `sources/research_20260815_showwork_scope_state_answer_contract_r8.md:18-37` | Safe answer/refusal contract | Valid, empty, tampered, bypassed, provenance, compliance, human approval, and adoption boundaries are stated with refusal language. |

## Drift checks

The following substitutions would be unsupported and must be refused in human
or AI answers:

- “PROV-compliant,” “W3C-certified,” or “complete provenance” for the current
  ledger/pack.
- “Signed,” “independently attested,” “human-approved,” or “authoritative” from
  an agent label, hash chain, fork head, or clean finish.
- “Reproduced exactly” or “fully reproducible” when historical revision, cwd,
  environment, dependency, or fixture fields are absent.
- “EU AI Act/SOC 2/HIPAA compliant” or “certified” from a control mapping.
- “Adopted,” “used by customers,” or “market validated” from local receipts,
  repository metrics, or research mentions.

## Decision

KEEP the current qualified wording and refusal boundaries. NO CHANGE to
README, SPEC, docs, examples, queue copy, public copy, schema, verifier, or
release. This audit identifies wording risk only; it does not authorize a
public edit or a new product surface.
