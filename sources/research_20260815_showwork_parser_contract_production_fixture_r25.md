# showwork r25 parser-contract production-fixture readout

Date: 2026-08-15  
Scope: disposable local fixture; report-only  
Card: `parser-contract-production-fixture-20260815-r25`

## Question

Does the current showwork verification path enforce the r24 evidence-pack
semantic contract when redacted receipt-shaped records are presented in
different forms?

The answer is bounded. `showwork` currently verifies its append-only JSONL
claim ledger, while `scripts/evidence_pack.py` generates a Markdown export
from that ledger. No inverse evidence-pack parser is present in the inspected
production path. This fixture therefore measures the behavior of the current
JSONL reader and verifier when receipt-shaped fields are added to a claim
record. It does not establish a future evidence-pack parser contract.

## Fixture and method

Disposable root:

`C:\Users\patri\AppData\Local\Temp\showwork-r25-parser-fixture-20260815`

The fixture contained only a redacted `marker.txt` with `verified` and one
`claims-2026-08-15.jsonl` record. The base record was:

```json
{"session":"parser-fixture","ts":"2026-08-15T00:00:00","claim":"redacted proof receipt is valid","severity":"RED","check":{"type":"file_contains","path":"marker.txt","pattern":"verified"},"proof_state":"verified","verdict":"GREEN","exit":0,"marker":"GREEN"}
```

Each mutation replaced that one JSONL input and ran the existing
`showwork.ledger.verify_date` path. The runner measured elapsed wall time in
the same Python process and removed the exact temporary root after the run.
The timing is fixture-process overhead, not a production latency threshold.

## Observed versus r24 contract

The r24 semantic expectation is included for comparison only: representation
changes may answer or qualify; missing decisive evidence should be unknown; a
malformed or contradictory proof should refuse.

| mutation | exact input change | r24 semantic expectation | current path | observation |
|---|---|---|---|---|
| canonical | base one-line JSON | answer | GREEN, 1/1 | file check passes; receipt-shaped fields are not interpreted |
| field-order | reverse JSON key order | answer | GREEN, 1/1 | JSON object order is tolerated |
| whitespace | pretty JSON with leading/trailing whitespace | answer | YELLOW, 0/15 | JSONL is line-oriented; each pretty-printed line becomes a parse error |
| marker-moved | move the `GREEN` marker into claim text | qualify | GREEN, 1/1 | marker location is not a verifier concept |
| missing-marker | remove `marker` | unknown | GREEN, 1/1 | missing marker is not checked |
| omitted-decisive | remove `verdict` | unknown | GREEN, 1/1 | missing verdict is not checked |
| malformed-value | set `exit` to string `zero` | refuse | GREEN, 1/1 | exit type is not checked |
| contradictory | `proof_state=verified` with `verdict=RED` | refuse | GREEN, 1/1 | contradiction is not checked |
| malformed JSON | truncate the JSON object | refuse/unknown | YELLOW, 0/1 | parse error is visible and does not become GREEN |

Observed read times were 5.8-74.5 ms per mutation in this single local
process. The first call was the coldest; no capacity, SLA, or production
performance conclusion follows from these values.

## Finding

The current ledger verifier is deterministic for the claim checks it knows,
but receipt-shaped fields outside the ledger contract are opaque. Valid
JSONL representations with missing, malformed, or contradictory proof fields
can still produce GREEN when the independent `file_contains` claim passes.
Pretty-printed multi-line JSON is not one JSONL record and becomes YELLOW.
That is a parser-boundary observation, not a recommendation to loosen or
tighten the production parser.

## Exact reproducer inputs

The base record above is the canonical reproducer. The mutations are
deterministic transforms:

```text
field-order       reverse all JSON object keys
whitespace        json.dumps(..., indent=2), surrounded by two spaces
marker-moved      claim += " GREEN"; retain marker field
missing-marker    delete marker
omitted-decisive  delete verdict
malformed-value   exit = "zero"
contradictory     proof_state = "verified" and verdict = "RED"
malformed-json    {"session":"parser-fixture","claim":
```

The fixture does not alter `src/`, `scripts/`, `README.md`, `SPEC.md`, the
dashboard, the serializer, the pack format, or any public surface.

## Owner gate

Any future parser or receipt-contract change requires an owner decision on
the input format, decisive fields, normalization rules, refusal taxonomy,
tests, and backward compatibility. This readout does not select an identity
scope, add a parser, claim replay safety, or claim human/agent comprehension.

## Verification

- `python -m showwork.ledger.verify_date` fixture run: completed; all rows recorded above.
- Exact temporary fixture removed: confirmed.
- Receipt status: GREEN; `4/5` current claims verify because one initial
  regex claim remains as a retracted append-only record and was superseded by
  a verifier-compatible claim. The retraction is preserved rather than
  rewritten.
- Full repository gate for this cycle: `python -m pytest tests/ -q` -> 240 passed.
