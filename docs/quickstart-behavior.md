# Behavior quickstart

The README file walk proves a path exists. This walk proves one function
result. It uses a standard-library test, not pytest.

Need Python 3.10 or newer. Check the interpreter first:

```bash
python --version
```

```powershell
python --version
```

Install, then inspect the install:

```bash
python -m pip install showwork
python -m showwork doctor
```

```powershell
python -m pip install showwork
python -m showwork doctor
```

`python -m showwork` is the same CLI after install. Use it if `showwork`
is not on PATH. Ten minutes is a target for this path. It is not a measured time.

Create a new empty directory and save these two files.

`add.py` is wrong on purpose:

```python
def add(a, b):
    return a + b + 1
```

`run_tests.py` is a standard-library runner:

```python
import sys
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
```

Declare a behavior check, then try to close. The close must refuse because
`add(2, 2)` is 5.

Bash:

```bash
python -m showwork start --session first-behavior --agent manual
python -m showwork require --session first-behavior --id add --scope behavior --description "add(2, 2) returns 4" --type command --command-arg python --command-arg run_tests.py --expect-exit 0 --stdout-contains passed
python -m showwork claim --session first-behavior --claim "test runner exists" --type file_exists --path run_tests.py
python -m showwork claim --session first-behavior --claim "add.py exists" --type file_exists --path add.py
python -m showwork finish --session first-behavior --status ok
```

PowerShell (same flags; no JSON braces):

```powershell
python -m showwork start --session first-behavior --agent manual
python -m showwork require --session first-behavior --id add --scope behavior --description "add(2, 2) returns 4" --type command --command-arg python --command-arg run_tests.py --expect-exit 0 --stdout-contains passed
python -m showwork claim --session first-behavior --claim "test runner exists" --type file_exists --path run_tests.py
python -m showwork claim --session first-behavior --claim "add.py exists" --type file_exists --path add.py
python -m showwork finish --session first-behavior --status ok
```

Expected: exit code `2`, a `RED` claims verdict, and a `REFUSED` message.
The failed close is part of this example.

Repair `add.py`:

```python
def add(a, b):
    return a + b
```

The `run_tests.py` and `add.py` claims are still true. Do not retract them.
Close again. If you skip the `add.py` claim, finish refuses the undeclared
change even after the unittest passes.

```bash
python -m showwork finish --session first-behavior --status ok
```

```powershell
python -m showwork finish --session first-behavior --status ok
```

Expected: exit code `0` and `Outcome: VERIFIED`.

That outcome covers `add(2, 2) == 4` through this unittest. The file-exists
checks name the files. They do not replace the unittest. They do not cover
other inputs, other functions, or whether the test matches a larger request.
A file-exists check alone is not this walk.

Copy the directory, including `.showwork/`, to a sibling folder. Rerun
the checks from the copy. Use a new empty destination.

Bash:

```bash
cp -a . ../first-behavior-copy
cd ../first-behavior-copy
python -m showwork verify --session first-behavior --no-report
```

PowerShell:

```powershell
Copy-Item -Recurse -Force . ..\first-behavior-copy
Set-Location ..\first-behavior-copy
python -m showwork verify --session first-behavior --no-report
```

Expected: exit code `0`.

For a real repository, `showwork init` writes Cursor, Claude, and CI
helpers. A second `init` skips files that already exist and merges
Claude settings. It does not replace your host config unless you pass
`--force`.

A shell-independent copy of this walk is in the
[Python quickstart](quickstart-python.md#behavior-walk).
[Return to the README](../README.md).
