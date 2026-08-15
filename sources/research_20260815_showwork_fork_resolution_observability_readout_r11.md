# showwork fork-resolution observability readout r11

Date: 2026-08-15  
Scope: retained local audit, sessions, claims, heads, and retraction records.
No authority field, signer, verifier, schema, public claim, compliance claim,
or human-approval inference.

## Commands and current evidence

Read-only commands:

```text
python -m showwork.cli audit --json
python -m showwork.cli verify --date 2026-08-15 --json --no-report
rg '"retracted": true' .showwork/claims-2026-08-15.jsonl
```

Current audit snapshot after the r11 session starts: whole corpus `YELLOW`,
487 records, 455 chained, 43 forks. The day claims file is `GREEN`, 135/135
chained, one fork across two heads. `sessions.jsonl` is `GREEN`, 199 records,
186 chained, 13 pre-chain, and 23 forks. The current claims file contains 17
append-only retraction records. Whole-corpus YELLOW reflects retained legacy
pre-chain history; it is not a claim that the current day file is tampered.

## Question-to-answer matrix

| Question | Current field evidence | Safe answer | Refusal boundary |
|---|---|---|---|
| Which heads were observed? | `audit --json` per-file `heads`, `head`, `forks` | Answer with the exact file, count, and head hashes | Do not call a head authoritative |
| Was a fork observed? | Per-file `forks` and multiple heads | Yes, for the audited file and snapshot | Fork existence is not resolution |
| Which head was selected? | No selected-head field in current audit/pack | Unknown unless external prose declares a choice | `head` means last line for compatibility, not selected authority |
| What was the selection basis? | No retained relation in current fields | Unknown | Do not infer from order, timestamp, hash, or “latest” wording |
| Which branches remain unresolved? | Multiple heads plus missing resolution relation | Report observed heads as unresolved where no selection relation exists | Do not choose a branch |
| What was retracted? | Retraction records identify a session/claim target when retained | Report the exact retained target and reason | Retraction does not prove who authorized it or what should replace it |
| Was a fork resolved by a human? | No reviewer/authority field | Unknown | Refuse human approval, authorship, attestation, or legal status |
| Is the pack complete? | Evidence-pack inventory is not a lifecycle graph | It contains bounded integrity/claim evidence | Refuse complete provenance or authority claims |

The ordinary audit may accept an intact fork as GREEN; strict mode may reject
forks as RED. Those are integrity-policy verdicts, not branch ownership or
human decisions.

Evidence paths:

- `K:\showwork\.showwork\claims-2026-08-15.jsonl`
- `K:\showwork\.showwork\sessions.jsonl`
- `K:\showwork\sources\research_20260815_showwork_fork_authority_owner_boundary_r10.md`
- `K:\showwork\sources\research_20260815_showwork_lifecycle_fork_retraction_answerability_r9.md`

## Decision

KEEP the current observable fields and refusal language. No implementation or
format change follows. Counts and hashes describe recorded ledger structure;
they do not establish authority, approval, authorship, attestation, legal
status, or adoption.
