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
behavior.

## Behavior walk

This second script uses a broken `add` function and a standard-library test.
The first close must refuse. After the repair, the close succeeds. A copy of
the directory then reruns the same checks.

Ten minutes is a target for the shell walk in
[behavior quickstart](quickstart-behavior.md). It is not a measured time.

```python
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

RUNNER = '''import sys
import unittest

from add import add


class AddTests(unittest.TestCase):
    def test_two_plus_two(self):
        self.assertEqual(add(2, 2), 4)


def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AddTests)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if result.wasSuccessful():
        print("passed")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
'''

with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    root = base / "orig"
    replica = base / "copy"
    root.mkdir()

    def run(cwd, *args, expected=0):
        result = subprocess.run(
            [sys.executable, "-m", "showwork", "--root", str(cwd), *args],
            cwd=cwd,
            text=True,
            capture_output=True,
        )
        print(result.stdout, end="")
        print(result.stderr, end="")
        assert result.returncode == expected, result

    run(root, "doctor")
    (root / "add.py").write_text(
        "def add(a, b):\n    return a + b + 1\n", encoding="utf-8"
    )
    (root / "run_tests.py").write_text(RUNNER, encoding="utf-8")
    run(root, "start", "--session", "first-behavior", "--agent", "manual")
    run(
        root, "require", "--session", "first-behavior",
        "--id", "add", "--scope", "behavior",
        "--description", "add(2, 2) returns 4",
        "--type", "command",
        "--command-arg", "python",
        "--command-arg", "run_tests.py",
        "--expect-exit", "0",
        "--stdout-contains", "passed",
    )
    run(
        root, "claim", "--session", "first-behavior",
        "--claim", "test runner exists",
        "--type", "file_exists", "--path", "run_tests.py",
    )
    run(
        root, "claim", "--session", "first-behavior",
        "--claim", "add.py exists",
        "--type", "file_exists", "--path", "add.py",
    )
    run(root, "finish", "--session", "first-behavior", "--status", "ok", expected=2)
    (root / "add.py").write_text(
        "def add(a, b):\n    return a + b\n", encoding="utf-8"
    )
    run(root, "finish", "--session", "first-behavior", "--status", "ok")
    shutil.copytree(root, replica)
    run(replica, "verify", "--session", "first-behavior", "--no-report")
```

Expected: the first close prints `REFUSED` and exits with code 2.
After the repair, the close prints `Outcome: VERIFIED` and exits with code 0.
The copy then verifies with exit code 0.

This proves `add(2, 2) == 4` through this unittest. The file-exists checks
name the files. They do not replace the unittest. They do not prove other
inputs or other functions. [Return to the README](../README.md).

