# showwork fork-authority owner boundary r10

Date: 2026-08-15  
Scope: synthetic complete, partial, and conflicting fork packs using existing
audit/head/retraction vocabulary. No authority field, signer, second verifier,
schema, legal wording, or public claim was added.

## Result

Observed heads are integrity evidence. A selected head is a declared choice.
Neither ordering, a hash link, a latest timestamp, nor a declared selection
proves independent authority or human approval. A conflicting pack must expose
the conflict and refuse an authoritative answer.

## Synthetic pack matrix

| Pack | Declared fields | Safe answer | Refuse |
|---|---|---|---|
| Complete, non-conflicting | Chain verdict, all heads, fork count, selected head, stated resolution basis | “These heads were observed; the pack declares this head selected under the stated basis.” | “The selected head is independently authoritative” or “a human approved it.” |
| Fork-partial | Chain verdict, fork count, two heads, no selection | “A fork with these observed heads exists.” | Which head is final, authoritative, or approved. |
| Conflicting selection | Two heads, two incompatible declared selections, no resolving authority | “The pack contains conflicting selections and cannot establish one final state.” | Any tie-break inferred from order, hash value, timestamp, or prose. |
| Retraction-linked but authority-absent | Retraction target and selected head are recorded, no reviewer or authority relation | “The selected state includes a recorded retraction link.” | Whether the retraction was authorized or the selected state is independently trustworthy. |

## Fixed query matrix

| Query | Complete | Partial/conflicting |
|---|---|---|
| Which heads were observed? | Answerable from audit heads | Answerable if heads are retained; otherwise refuse |
| Which head was selected? | Report the declared selection | Refuse if absent; report conflict if incompatible selections exist |
| Why was it selected? | Quote the declared basis only | Refuse if no basis is retained |
| Is it authoritative? | Refuse independent authority; report only “declared selected” | Refuse |
| Did a human approve it? | Refuse; no human authority field | Refuse |
| Is the fork resolved? | Conditional on an explicit retained resolution relation | Refuse when only heads/counts are present |

The existing ordinary audit can remain `GREEN` for an intact fork while
exposing heads. Strict mode can treat forks as `RED`, but neither verdict
chooses the authoritative branch. A tamper-evident chain proves the relation
between recorded bytes, not the correctness or ownership of a branch choice.

Evidence paths:

- `K:\showwork\sources\research_20260815_showwork_lifecycle_fork_retraction_answerability_r9.md`
- `K:\showwork\sources\research_20260815_showwork_provenance_field_crosswalk_readout_r9.md`
- `K:\showwork\sources\research_20260815_showwork_scope_state_answer_contract_r8.md`
- `K:\showwork\.showwork\claims-2026-08-15.jsonl`
- `C:\Users\patri\Documents\Obsidian Vault\Reports\Research\showwork-lifecycle-fork-retraction-answerability-2026-08-15.md`

## Decision

KEEP the observed-head/declared-selection/authority distinction. NO CHANGE to
the ledger, pack, verifier, or public copy. Any external authority, human
approval, legal, or attestation statement remains owner-gated.
