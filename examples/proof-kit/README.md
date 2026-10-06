# Three failures you can repair

The kit runs three toy paths with the Python environment you select. It needs
Python 3.10 or newer and showwork, with no model, BMD account or paid service.
The runner creates a new directory and refuses an existing one. It changes and
removes only its own toy files. The driver writes each repair; an agent does
not author these tasks.

Start with the public package in a clean environment:

```text
python -m venv proof-env
```

On Windows:

```powershell
.\proof-env\Scripts\python.exe -m pip install --index-url https://pypi.org/simple showwork==0.6.6
.\proof-env\Scripts\python.exe -O examples/proof-kit/run.py proof-results
```

On Linux/macOS:

```bash
proof-env/bin/python -m pip install --index-url https://pypi.org/simple showwork==0.6.6
proof-env/bin/python -O examples/proof-kit/run.py proof-results
```

Run these from a downloaded showwork repository containing this example. The
script uses the installed distribution, not `src/`. Keep `PYTHONPATH` unset
when testing that public install. The example kit is source documentation;
publication of this source revision as a new Python package is separate.

| Example | Deliberate failure | Repair and current check | Limit |
| --- | --- | --- | --- |
| Declared test failure | The real `add(2,2)` returns 5; finish exits 2 | Repair the function; finish exits 0; copy to a fresh directory and verify again | One input only; completeness of the user's requirements is unknown |
| Undeclared damage | Delete an existing unclaimed toy input after start; finish exits 2 even though the function probe passes | Restore its original bytes; finish and current verify pass | Existing snapshot coverage only; no promise to cover every new file or external effect |
| Handoff | A fresh process reads a copied producer receipt after its command breaks | Reading executes no inherited command and preserves receipt bytes; explicit rerun fails; a fresh consumer session independently verifies the repair | Client names are driver labels, not actual host task execution; no approval transfers |

Choose `--example failure`, `--example damage` or `--example handoff` to run one
path. The runner uses explicit predicates under `python -O`; a broken acceptance
check fails loudly. Toy failures, repairs and reruns are printed as observations,
not a general detection rate or customer outcome.

Public 0.6.6 reads the handoff receipt with the bounded process-free reader. It
starts no process and runs no inherited command. Version 0.6.5 and earlier
used a receipt overlay that disabled the recorded behavior command and reported
unknown. Neither view performs current behavior acceptance or grants permission
to merge.

## Report or contribute

- [Report a reproducible bug](https://github.com/bmdhodl/showwork/issues/new/choose): include package version, Python/host version, minimal safe files, expected/observed exits and a redacted receipt. Keep credentials and private transcripts out.
- Add one [reader conformance fixture](../../docs/readers.md) that fails before the fix and matches in Python and JavaScript. A receipt label alone is insufficient.
- Improve one [host recipe](../../docs/claude-code.md) with the supported version, actual native lifecycle evidence, refusal/repair proof and an uninstall check. A simulated payload is not actual host completion.

Use [the contribution contract](../../CONTRIBUTING.md): maintainer review, full
tests, a distinct writer, acceptance before claims, strict finish and the
committed receipt gate remain required. These are bounded contributions, not
permission to change the ledger, trust policy or publishing authority.
