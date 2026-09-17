# Python quickstart

Install `showwork` with Python 3.10 or newer:

```bash
python -m pip install showwork
```

Save the following as `try_showwork.py`, then run `python try_showwork.py`.
It creates a temporary directory and uses the installed CLI through Python,
so it does not depend on your shell's JSON quoting.

```python
from pathlib import Path
import json
import subprocess
import sys
import tempfile

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)

    def run(*args, expected=0):
        result = subprocess.run(
            [sys.executable, "-m", "showwork", "--root", str(root), *args],
            cwd=root,
            text=True,
            capture_output=True,
        )
        print(result.stdout, end="")
        print(result.stderr, end="")
        assert result.returncode == expected, result

    run("start", "--session", "first-look", "--agent", "manual")
    run(
        "require", "--session", "first-look",
        "--id", "config", "--scope", "artifact",
        "--description", "config/api.yaml exists",
        "--check-json", json.dumps({"type": "file_exists", "path": "config/api.yaml"}),
    )
    run(
        "claim", "--session", "first-look",
        "--claim", "config/api.yaml exists",
        "--type", "file_exists", "--path", "config/api.yaml",
    )
    run("finish", "--session", "first-look", "--status", "ok", expected=2)
    (root / "config").mkdir()
    (root / "config/api.yaml").write_text("timeout: 30\n", encoding="utf-8")
    run(
        "retract", "--session", "first-look",
        "--claim", "config/api.yaml exists", "--reason", "file was not written yet",
    )
    run(
        "claim", "--session", "first-look",
        "--claim", "config/api.yaml exists",
        "--type", "file_exists", "--path", "config/api.yaml",
    )
    run("finish", "--session", "first-look", "--status", "ok")
```

Expected: the first close prints `REFUSED` and exits with code 2.
After creating the file, the close prints `Outcome: VERIFIED` and exits with
code 0. The temporary directory and its receipts are removed when the example
ends. Use a persistent project directory for real work.

This example verifies a file's existence. It makes no claim about application
behavior. [Return to the README](../README.md).
