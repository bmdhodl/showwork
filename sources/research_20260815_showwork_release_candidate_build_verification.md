# showwork 0.3.1 release-candidate build verification

Date: 2026-08-15  
Source revision: 45da572  
Scope: local build and disposable installation only. No tag, publish, release,
metadata edit, or public artifact change.

## Candidate evidence

| check | result |
|---|---|
| wheel | showwork-0.3.1-py3-none-any.whl |
| sdist | showwork-0.3.1.tar.gz |
| wheel metadata | Name showwork, Version 0.3.1, Requires-Python >=3.10 |
| wheel SHA-256 | 3CDB977A1F881E8E4E7C66261E54FF768036AD5141C8F5051C903B83DA1D41BB |
| sdist SHA-256 | 5240CE335E5ADAD5E1ADC14D41D0CD5B8E44F6207F044CD7CEBEB48866910306 |
| installed version | 0.3.1 in a disposable virtual environment |
| first proof | start, file_exists claim, finish, and session verify GREEN |
| installed audit | GREEN, 3/3 records chained |
| sdist contents | README present; scripts/evidence_pack.py absent |
| test suite | 240 passed |

The package runtime path works from the wheel without repository checkout
dependencies. The evidence-pack script remains checkout-only for this
candidate and must not be implied to ship in the wheel.

## Decision

This is a local release-candidate verification, not release readiness or
publication authorization. A future owner-gated release must recheck the
intended public version, rendered description, action references, artifact
hashes, and checkout-only script boundary before publishing.

Validation: python -m pytest tests/ -q --basetemp=<temp>\showwork-release-hardening-full-20260815 -> **240 passed**
