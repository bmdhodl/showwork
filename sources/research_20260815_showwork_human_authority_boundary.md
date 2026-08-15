# showwork human-authority boundary

Date: 2026-08-15
Scope: synthetic lifecycle fixtures. No identity field, signing layer,
second verifier, legal conclusion, public-copy, schema, or release change.

## Result

The receipt can show that a named session started, which free-form agent label
was supplied, which deterministic claims passed or failed, whether the run was
blocked, whether a claim was retracted, and whether verification was bypassed.
It cannot show that a human approved, reviewed, delegated, witnessed, or
independently attested to the work. A note such as `human decision required`
is agent-written text, not proof that a human made the decision.

## Fixture results

The disposable fixture contained five sessions and 15 chained records:

| Case | Recorded lifecycle | What a reader can safely infer | What remains unknown |
|---|---|---|---|
| `owner-local` | `agent: codex`, one passing claim, `finish status: ok`, `claims_verdict: GREEN` | An owner-local process recorded a passing deterministic claim and closed cleanly | Which human, if any, initiated or approved it |
| `agent-worker` | `agent: worker`, one passing claim, `finish status: ok`, `claims_verdict: GREEN` | The supplied agent label and local verification result | Whether the label is authentic, which model or parent agent ran, and whether anyone reviewed the work |
| `blocked-run` | `finish status: blocked`, note `human decision required` | The session recorded a blocked close and stopped without a clean success claim | Whether a human saw the note, who had authority, or what decision was made |
| `retracted-run` | A failed claim was followed by an append-only retraction and `finish status: ok` with `GREEN (0/1 verified)` | The failed assertion and its retraction remain visible; the retracted claim is not active proof | Why a human retracted it, whether the underlying task was later done, or whether the retraction was authorized |
| `bypassed-run` | A failing claim was closed with `verify_bypassed: true`; export showed `XX` for the claim | The exit gate was deliberately bypassed and the bypass is durable | Whether the bypass was authorized or justified |

The fixture audit itself was `GREEN` with 15/15 chained records and no forks.
That proves ledger integrity, not human authority.

## Provenance boundary

The `agent` value is a free-form session field. The `prev` hashes and audit
heads establish continuity of the recorded bytes. Neither establishes a
human principal, an authenticated account, a source checkout, a commit
signature, a hardware root, or an external witness. The current receipt
surface therefore has these distinct reader labels:

- **Owner-local evidence:** local process and local deterministic checks are
  visible; no independent endorsement is implied.
- **Agent-labelled evidence:** a supplied agent string is visible; identity is
  not authenticated by the receipt.
- **Blocked or bypassed:** process state is visible; approval is not.
- **Retracted:** the correction is visible; the original claim is not current
  proof.
- **Human-reviewed or externally attested:** unknown unless a separate,
  independently controlled record exists outside showwork.

The [EU AI Act consolidated text](https://eur-lex.europa.eu/eli/reg/2024/1689/oj)
discusses human oversight for in-scope high-risk systems, including competence,
training, and authority. That legal requirement cannot be inferred from a
showwork `agent` field or a clean finish event.

## Decision

NO CHANGE. Keep owner-local, human-reviewed, externally reviewed, and
unverifiable as separate classifications. Do not add identity fields or
signing from this fixture.
