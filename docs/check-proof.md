# I tested Jev against weak completion evidence

**Status: the live pilot passed; hosted launch is being verified.**
The planned page is <https://bmdpat.com/tools/showwork/check-proof> and the
planned POST endpoint is <https://bmdpat.com/api/showwork/check-proof>.
Do not describe either as a validated live service until deployment readback
and the published holdout evaluation pass.

This experiment asks whether supplied evidence supports a completion claim.
Jev can flag a mismatch for review. It cannot authenticate evidence, execute
tests, approve releases, or change a showwork verdict. The deterministic CLI,
ledger format and exit gate do not use Jev.

## A passing check can miss the claim

I had a check that found a test count in a file. The file was handwritten.
The check passed. It did not prove that the test suite ran. The
[evidence-scope incident](evidence-scope.md) records that limit in showwork.

On September 17, 2026, I tested Jev as a second, advisory check. It receives
the requested outcome, completion claim, test source and execution output.
It chooses between support, a scope gap, contradiction and missing context.
The explanations come from fixed application copy. The model does not write them.

I pinned `jev-1.13.0` and wrote 60 labeled cases: 20 development and 40 held
out. They are authored examples, not an independent production sample. Labels
and rationales never entered the model request. I froze the question, cases
and model before the holdout, with no edits after the development run.

| Holdout measure | Jev | Conservative text baseline |
| --- | ---: | ---: |
| False support among 20 inadequate cases | 0 | 0 |
| Inadequate cases flagged | 20/20 | 10/20 |
| Adequate cases recognized | 10/10 | 0/10 |
| Insufficient-context cases recognized | 10/10 | 10/10 |

All 40 holdout labels matched. Five answers still fell below the 0.8 confidence
threshold and required review. Median provider latency was 178 ms; p95 was
347 ms. The 40 calls consumed 28,656 input and 2,300 output tokens, with no
service errors. Those timings exclude browser rendering and rate-limit checks.
They do not predict latency or accuracy for arbitrary submissions.

The development run matched 19 of 20 labels. Its miss matters: I labeled a
mocked email queue acceptance as a scope gap against a claim of inbox delivery.
Jev called it a contradiction, with confidence 0.54. The supplied evidence said
no email left the process, so the label boundary is debatable. I kept the original
label and report. I did not tune the question to turn that mismatch into a win.

The [holdout report](https://bmdpat.com/data/showwork/jev-holdout-2026-09-17.json),
[development report](https://bmdpat.com/data/showwork/jev-development-2026-09-17.json),
[baseline](https://bmdpat.com/data/showwork/baseline-2026-09-17.json),
[fixtures](https://bmdpat.com/data/showwork/check-proof-cases.json) and
[rubric](https://bmdpat.com/data/showwork/check-proof-rubric.json) include the
rows, confusion matrices, failures, token usage, model version and source hashes.
The baseline recognizes no adequate cases. Zero false support alone would hide
that failure, which is why the pilot also required useful recognition.

These results pass the small pilot's launch thresholds. They do not prove
authenticity, establish a general error rate, or approve any release. Jev cannot
tell whether a pasted execution receipt was invented. I still need deterministic
checks and independent review.

The integration uses TypeSafe's [direct HTTP API](https://docs.typesafe.ai/api)
and its [claim-versus-evidence pattern](https://docs.typesafe.ai/cookbooks/citation_check).
The [interactive checker](https://bmdpat.com/tools/showwork/check-proof) accepts
examples or text you choose to submit. No repository upload is automatic.

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
redirects, caps input at 32 KiB, and makes one request with a ten-second total deadline.
`--endpoint http://127.0.0.1:3000/api/showwork/check-proof` selects a local server.
Loopback requests bypass configured proxies. Non-local endpoints require HTTPS.
Nothing scans your repository or appends
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

[Try showwork locally](../README.md#quickstart).
