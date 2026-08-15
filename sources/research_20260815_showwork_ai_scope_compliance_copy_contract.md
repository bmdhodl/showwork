# showwork AI scope and compliance answer contract

Date: 2026-08-15
Scope: answerability research only. No README edit, public-copy change,
legal advice, compliance claim, schema, signing, release, or adoption claim.

## Result

KEEP a narrow answer contract for AI-facing and developer-facing questions:
showwork proves selected deterministic claims about a local workspace and
preserves the receipt history. It does not establish legal compliance, a full
AI audit trail, security certification, human approval, provenance, privacy,
or adoption.

The [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)
is intended for voluntary use and is a broad risk-management framework. The
current consolidated [EU AI Act](https://eur-lex.europa.eu/eli/reg/2024/1689/oj)
contains role-, system-, and risk-specific duties. Article 12 concerns
automatic event recording for high-risk systems; Articles 19 and 26(6) address
retention in specific provider/deployer contexts. A receipt tool cannot answer
those scope questions by itself.

## Fixed answer contract

| Question | Shortest supported answer | Proof source | Must not imply |
|---|---|---|---|
| Is showwork EU AI Act compliant? | Unknown and owner/counsel-gated. showwork is a deterministic receipt verifier, not a conformity assessment. | [docs/compliance.md](../docs/compliance.md), [EU AI Act](https://eur-lex.europa.eu/eli/reg/2024/1689/oj) | Legal compliance or certification |
| Does a receipt satisfy Article 12? | It can demonstrate an append-only event/claim recording mechanism for the tested workspace. Sufficiency for an in-scope high-risk system is unknown. | [SPEC.md](../SPEC.md), [README.md](../README.md), EU Article 12 | That the system, operator, or use is in scope or compliant |
| Does showwork implement NIST AI RMF? | It can support deterministic evidence for selected governance questions. NIST RMF alignment and implementation are owner assessments. | [README.md](../README.md), [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework) | NIST endorsement or a completed RMF |
| Is this a complete AI audit trail? | No. It is a falsifiable-claim ledger with chain verification and an evidence-pack renderer. | [README.md](../README.md), [docs/compliance.md](../docs/compliance.md) | Complete prompts, model versions, tool calls, data access, policy decisions, or downstream effects |
| Does a clean finish prove human approval? | No. It proves only that the session's recorded deterministic claims passed the configured verifier. | `src/showwork/ledger.py`, human-authority fixture | Human review, authorization, delegation, or sign-off |
| Does the chain prove security? | No. It proves a defined integrity property of the ledger bytes and refuses a tampered chain. | [SPEC.md](../SPEC.md), `showwork audit` | Security, confidentiality, availability, or threat absence |
| Does it prove provenance or a signer? | No. The receipt carries local chain links and a free-form agent label. Signing, hardware provenance, and external witnessing are separate concerns. | [README.md](../README.md) roadmap and provenance report | Authenticated authorship or independent attestation |
| Does redaction prove privacy? | No. `--redact` masks selected session/claim text in a rendered pack and leaves the ledger unchanged. | [docs/compliance.md](../docs/compliance.md), redaction fixture | Data minimization, lawful processing, deletion, or a privacy guarantee |
| Does showwork have adoption? | Not established by local receipts, repository metrics, or a public artifact. | Evidence-pack demand readout and public-proof reports | Customers, external users, or market adoption |
| Can a pack support SOC 2, HIPAA, or another audit? | It may be supporting evidence for an auditor to assess. Sufficiency is owner-, auditor-, and counsel-gated. | [docs/compliance.md](../docs/compliance.md) | Certification or framework compliance |

## Unsupported-claim list

The answer must say unknown or owner-gated for: legal classification; compliance
or certification; human approval; authenticated identity; model or parent-agent
identity; complete action and data lineage; privacy or security guarantees;
signing or hardware attestation; independent review; and adoption.

AI-crawler answerability and human adoption are separate. A clear answer in a
README or search result is not evidence that a buyer, user, or independent
reviewer adopted the project.

## Decision

NO CHANGE. Use this as an internal response contract only. Any future public
copy change requires a separate owner-gated review of exact claims and current
source text.
