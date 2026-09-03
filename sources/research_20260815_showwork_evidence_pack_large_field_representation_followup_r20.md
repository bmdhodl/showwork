# showwork r20: evidence-pack large-field representation follow-up

Date: 2026-08-15  
Scope: disposable local ledgers with synthetic large claim fields. No packer, serializer, production receipt, or performance promise changed.

## Probe

The fixture contained 40 claims with large claim text and a valid chain. The same evidence was compared as a full pack, a bounded synthetic reader projection, and a field-separated synthetic reader projection.

| representation | output bytes | exact full claim retained | truncation marker | check field retained | pack result |
|---|---:|---|---|---|---|
| full pack | 174344 | true | false | true | exit 0 |
| bounded projection | 170184 | false | true | true | reader-only |
| field-separated projection | 173879 | true | false | true | reader-only |

Five local repetitions produced parse times of 0.8335 to 1.0006 ms (median 0.9019 ms). Chain-audit times were 1.8268 to 2.1142 ms (median 1.8965 ms), and every valid audit returned GREEN. These are disposable measurements, not a baseline or SLA.

A malformed control caused pack generation to exit 2, returned a RED audit, and included `REFUSED`. The failure remained visible rather than being converted to a usable pack. The bounded representation reduced bytes but lost the exact claim text, while the field-separated representation retained the proof fields tested here.

## Boundary and recommendation

Representation choice changes what a reader can prove even when the underlying chain is valid. A future reader should mark truncation and preserve a link to complete evidence; it must not call a bounded projection equivalent to the full receipt. An **owner-gated** profiling/content review can choose a representation policy after a larger corpus is measured.

No serialization change, redaction of production receipts, schema change, performance claim, or hosted-service behavior is supported by this fixture.

Validation: `python -m pytest tests/ -q --basetemp=<temp>\showwork-r20-full-20260815` -> **239 passed**
