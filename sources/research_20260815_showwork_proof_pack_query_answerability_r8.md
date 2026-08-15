# showwork proof-pack query answerability

Date: 2026-08-15
Scope: fixed queries over synthetic/local proof packs. No second verifier,
human-signing model, legal language, public copy, schema, release, hosted
service, or adoption claim.

## Result

KEEP the current evidence-pack format and answer only what its fields support.
The pack answers bounded integrity and predicate questions. It conditionally
answers selected policy/retention questions as “the pack contains a mapping,”
not “the system is compliant.” It must refuse human approval, complete
provenance, independent attestation, and adoption questions.

## Synthetic packs

- **Valid pack:** one closed synthetic session, one `file_exists` claim, chain
  GREEN 3/3, claim GREEN 1/1, pack written.
- **Empty pack:** same intact fixture with an out-of-range date, zero sessions
  and zero claims, chain GREEN, claim GREEN 0/0.
- **Authority/bypass pack:** synthetic owner, worker, blocked, retracted, and
  bypassed sessions; pack showed one bypass and an `XX` claim. No human field.
- **Tampered pack:** prior disposable fixture with chain RED; pack refused and
  wrote no file.

## Fixed query matrix

| Question | Result | Supporting pack field | Required refusal or qualifier |
|---|---|---|---|
| Was a bounded claim recorded? | Answerable for valid non-empty pack | Session count, claim inventory, timestamp | State exact date range and pack scope |
| What predicate was checked? | Answerable | Check type and receipt status | Do not infer unlogged actions or inputs |
| Does the claim verify now? | Answerable | `OK`, `XX`, or `..` in inventory | Current verification is not permanent truth |
| Was the ledger chain intact? | Answerable for the export | Chain verdict, counts, and heads | RED chain means refuse the pack |
| Did a fork exist? | Conditional | Audit data, not reliably the pack inventory | Do not infer fork state if only the pack is held |
| Was a claim retracted or bypassed? | Conditional | Pack summary and retained ledger context | The pack is not a complete lifecycle graph |
| Who approved the work? | Refuse | No human reviewer/authority field | Agent label is not human approval |
| What source revision or environment produced it? | Refuse | Command checks lack revision/cwd fields | Provenance is incomplete |
| Is it legally compliant or audit-certified? | Refuse/owner-gated | Control mapping is explanatory evidence only | NIST and W3C context are not certification |
| Is there adoption or an external customer? | Refuse | No adoption field | Local receipts are not market evidence |

The [W3C PROV primer](https://www.w3.org/TR/prov-primer/) provides a useful
comparison: entities, activities, agents, responsibility, and time can form a
provenance record. showwork's current pack contains some analogous evidence,
but does not declare a PROV graph or authenticated responsibility relation.
The [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework) is
voluntary risk-management guidance, not an answer that a local pack can prove.

## Decision

NO CHANGE. Keep the query matrix internal and keep unsupported questions as
refusals. No schema or second verifier follows from these synthetic packs.
