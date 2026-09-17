# Optional Jev evidence assessment

**Status: implementation prepared; live evaluation and hosted launch pending.**
The planned page is <https://bmdpat.com/tools/showwork/check-proof> and the
planned POST endpoint is <https://bmdpat.com/api/showwork/check-proof>.
Do not describe either as a validated live service until deployment readback
and the published holdout evaluation pass.

This experiment asks whether supplied evidence supports a completion claim.
Jev can flag a mismatch for review. It cannot authenticate evidence, execute
tests, approve releases, or change a showwork verdict. The deterministic CLI,
ledger format and exit gate do not use Jev.

## Explicit input only

From a source checkout, prepare a JSON file with four string fields:
`requested_outcome`, `claim`, `check`, and `evidence`. A public illustrative
case is in `examples/check_proof_input.json`. Do not include secrets or private
repository content. Submitting sends these fields to the hosted service and
TypeSafe, under [TypeSafe's privacy policy](https://typesafe.ai/legal/privacy-policy).
The application does not retain submitted text. That is not a promise about
the provider's retention policy.

```bash
python examples/check_proof.py --input examples/check_proof_input.json
```

The example uses the standard library. It reads only the selected file, refuses
redirects, caps input at 32 KiB, and makes one request with a ten-second timeout.
`--endpoint http://127.0.0.1:3000/api/showwork/check-proof` selects a local server.
Non-local endpoints require HTTPS. Nothing scans your repository or appends
to `.showwork/`. No TypeSafe credential belongs in this public client.

Exit `0` means an advisory response was obtained, **not** that the work passed.
Exit `2` means invalid input or an unavailable assessment. A disabled or
unlaunched endpoint returns an error; no simulated verdict is substituted.

## Interpretation

| Result | What it means |
| --- | --- |
| `appears_supported` | Supplied text appears to match the claim. Authenticity is unverified. |
| `scope_gap` | The check covers less than, or something different from, the claim. |
| `contradicted` | Supplied evidence conflicts with the claim. |
| `insufficient_context` | Relevant test source or evidence is missing or ambiguous. |

The response includes probabilities, confidence, model/rubric version, token
usage, latency and `advisory: true`. Confidence below 0.8 sets `requires_review`.
High confidence is not a guarantee. Keep running the
[deterministic quickstart](../README.md#quickstart) and relevant behavior tests.

The public pilot is capped at five requests per IP per hour and 200 total per
rolling day. The endpoint fails closed if its persistent quota cannot be checked.
There is no paid tier in this experiment.
