# showwork proof-pack size, latency, and fidelity r24

Date: 2026-08-15  
Source revision: 6f55b4a  
Method: in-memory redacted packets, Python 3.13.2 on Windows 11
10.0.26200-SP0, 25 timing repeats per cell. These are local microbenchmark
observations, not a production threshold, SLA, capacity, or parser result.

## Matrix

Readers were plain, structural, and AI-shaped. Each received the same
classification. `read_us` is the median standard-library fixture read or
handled refusal; `projection_us` is the median bounded string projection.

| claim length | shape | bytes | read_us | projection_us | exact claim | disclosure | classification |
|---:|---|---:|---:|---:|---|---|---|
| 64 | full | 199 | 1.600 | 0.100 | yes | no | answer |
| 64 | field-separated | 171 | 1.000 | 0.100 | yes | no | answer |
| 64 | bounded-with-marker | 213 | 1.100 | 0.100 | no | yes | qualify |
| 64 | malformed | 29 | 2.000 | 0.100 | no | no | refuse |
| 64 | contradictory | 199 | 1.500 | 0.100 | no | no | refuse |
| 512 | full | 647 | 1.800 | 0.100 | yes | no | answer |
| 512 | field-separated | 619 | 1.200 | 0.100 | yes | no | answer |
| 512 | bounded-with-marker | 277 | 1.200 | 0.100 | no | yes | qualify |
| 512 | malformed | 29 | 1.800 | 0.100 | no | no | refuse |
| 512 | contradictory | 647 | 1.800 | 0.100 | no | no | refuse |
| 2048 | full | 2183 | 2.500 | 0.100 | yes | no | answer |
| 2048 | field-separated | 2155 | 1.700 | 0.100 | yes | no | answer |
| 2048 | bounded-with-marker | 277 | 1.100 | 0.100 | no | yes | qualify |
| 2048 | malformed | 29 | 1.900 | 0.100 | no | no | refuse |
| 2048 | contradictory | 2183 | 2.600 | 0.100 | no | no | refuse |
| 4096 | full | 4231 | 3.500 | 0.100 | yes | no | answer |
| 4096 | field-separated | 4203 | 2.100 | 0.100 | yes | no | answer |
| 4096 | bounded-with-marker | 277 | 1.200 | 0.100 | no | yes | qualify |
| 4096 | malformed | 29 | 1.900 | 0.100 | no | no | refuse |
| 4096 | contradictory | 4231 | 3.600 | 0.100 | no | no | refuse |

Full and field-separated packet bytes grow with claim length and retain the
exact claim. The bounded projection stays small but loses exact claim fidelity
and therefore only qualifies when its disclosure marker is present. Malformed
and contradictory packets refuse for every reader shape. The projection timing
is a string-slice fixture and must not be generalized to a production UI or
network path.

## Boundary

This readout does not choose a byte budget, latency target, serializer, packer,
or UI behavior. It is not an SLA or capacity result and makes no
human-comprehension or adoption claim. Any budget decision remains
owner-gated.

Validation: `python -m pytest tests/ -q` -> **240 passed**.
