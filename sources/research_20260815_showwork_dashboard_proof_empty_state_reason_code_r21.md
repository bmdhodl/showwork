# showwork r21: dashboard empty-state reason-code visibility

Date: 2026-08-15  
Scope: disposable HTML fixtures around the existing dashboard output. No
dashboard, UI, tracking, public-copy, or accessibility change.

## Label matrix

| fixture | bytes | visible state detected | role=status nodes | reader class |
|---|---:|---|---:|---|
| no label | 3899 | none | 0 | unknown |
| No proof evidence. | 3938 | no evidence | 1 | human-readable state |
| Verified empty scope. | 3941 | verified empty | 1 | human-readable state |
| Proof failed: RED. | 3938 | RED | 1 | human-readable state |
| Close refused. | 3934 | refused | 1 | human-readable state |
| Run blocked. | 3932 | blocked | 1 | human-readable state |
| data-proof-reason=RED, text RED | 3947 | no human phrase | 1 | machine-readable-only reason code |

The base output remained unknown: its zero-value counters and generic warning
did not establish any proof state. Each plain-language label separated the
tested states in the disposable text reader. A reason code alone was useful to
a machine that knows the vocabulary but was not a sufficient human explanation.
The role=status observation is structural evidence for the fixture only; it is
not an accessibility-conformance claim.

## Reader boundary and recommendation

The no-label fixture remains vulnerable to false-green and false-red readings
because an empty result is not a proof verdict. A minimal human-readable state
label reduced that ambiguity in the fixture; a code-only label preserved an
interpretation gap. An owner-gated content-contract review may define the
smallest state label and reason vocabulary, with explicit tests for no
evidence, verified empty, RED, refused, and blocked.

No dashboard implementation, UI, tracking, public-copy, accessibility,
schema, adoption, or compliance change belongs to this readout.

Validation: python -m pytest tests/ -q --basetemp=C:\Users\patri\AppData\Local\Temp\showwork-r21-full-20260815 -> **239 passed**
