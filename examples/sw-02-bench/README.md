# SW-02 bench fixture

Eight frozen cases for issue #87. The seed is a tiny `add(2, 2)` app.
`run.py` copies the seed, then measures pytest and showwork. Set
`SW02_AGENT_VERIFY` to an Agent Verify checkout to measure
`node src/cli.mjs --message`.

```bash
python examples/sw-02-bench/run.py --out docs/reports/sw-02-benchmark/results.json
```

With Agent Verify:

```bash
set SW02_AGENT_VERIFY=C:\path\to\agent-verify
python examples/sw-02-bench/run.py --out docs/reports/sw-02-benchmark/results.json
```

Do not clone Agent Verify into this repository. CI replays pytest and
showwork only. Committed `results.json` stores the dated Agent Verify run.

The readout is `docs/reports/sw-02-benchmark/README.md`.
