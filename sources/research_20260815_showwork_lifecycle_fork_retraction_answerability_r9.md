# showwork lifecycle fork/retraction answerability r9

Date: 2026-08-15  
Scope: declared synthetic/local pack fixtures used to test answer and refusal
boundaries. No ledger schema, second verifier, signer, public claim, or
production policy was changed.

## Result

Lifecycle questions are answerable only to the extent that the pack retains
the relevant relation. A fork count can establish that a fork was observed,
but not which head is authoritative when resolution is absent. A retraction
row without its originating claim can establish that a retraction record
exists, but not what content it retracts. “Declared final head” is not the
same as independent authority.

## Synthetic packs

The fixtures below are in-memory declarations over the existing showwork
field vocabulary. They were used as a fixed query matrix, not persisted as a
new format.

| Pack | Declared lifecycle detail | What is intentionally missing |
|---|---|---|
| Complete lifecycle | Chain verdict/head, fork count and both heads, selected/final head, retraction row linked to its originating claim, sessions and claim statuses | Independent authority or human approval |
| Fork-partial | Chain verdict/head, fork count, and two observed heads | Fork-resolution relation and basis for selecting an authoritative head |
| Retraction-partial | Chain verdict/head and a retraction row | Originating claim identifier/content and reason linkage |
| Lifecycle-absent | Chain verdict/head and ordinary claim status | Fork, retraction, resolution, and lifecycle relations |

## Fixed query matrix

| Query | Complete | Fork-partial | Retraction-partial | Lifecycle-absent |
|---|---|---|---|---|
| Did a fork exist? | Answerable from fork count/heads | Answerable as “a fork was recorded” | Refuse; no fork field | Refuse |
| What was retracted? | Answerable only through the retained claim link | Refuse; no retraction relation | Conditional: a retraction row exists, but its target is unknown | Refuse |
| Is the final state authoritative? | Report only “the pack declares a final/selected head”; refuse independent authority | Refuse resolution/authority | Refuse resolution/authority | Refuse |
| Is the pack lifecycle-complete? | Answerable as “all tested lifecycle fields are present” | No; report partial | No; report partial | No; lifecycle detail is absent |

The answer “a fork was recorded” is narrower than “the fork was resolved.”
The answer “a retraction row exists” is narrower than “claim X was
retracted.” Any missing relation turns the stronger question into a refusal,
not an inference from ordering or prose.

## Evidence boundary

The field and query choices follow the existing local readouts:

- `K:\showwork\sources\research_20260815_showwork_proof_pack_query_answerability_r8.md`
- `K:\showwork\sources\research_20260815_showwork_scope_state_answer_contract_r8.md`
- `C:\Users\patri\Documents\Obsidian Vault\Reports\Research\showwork-proof-pack-query-answerability-2026-08-15.md`
- `C:\Users\patri\AppData\Local\Temp\showwork-governance-human-authority-20260815-r1`

The existing audit already exposes fork counts and heads, while the evidence
pack is not a complete lifecycle graph. The human-authority fixture exposes
owner-local, worker, blocked, retracted, and bypassed session states, but no
human reviewer or independent authority field.

## Decision

KEEP the current bounded answer/refusal language. NO CHANGE to the ledger or
pack format follows. Do not infer human authority, legal compliance,
attestation, adoption, or a resolved fork from partial lifecycle evidence.
