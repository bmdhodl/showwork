"""Run the test suite; exit 0 on green.

Exists so showwork's own ledger can carry a locked `command` claim that the
suite passes ("command" claims run `python <script under project root>` only).
"""

import subprocess
import sys
import tempfile

with tempfile.TemporaryDirectory(prefix="showwork-pytest-") as basetemp:
    result = subprocess.run([
        sys.executable,
        "-m",
        "pytest",
        "tests/",
        "-q",
        f"--basetemp={basetemp}",
    ])
raise SystemExit(result.returncode)
