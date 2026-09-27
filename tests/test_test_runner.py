"""The acceptance runner propagates failure and cleans its own scratch tree."""

from pathlib import Path
import shutil
import subprocess
import sys

import pytest


@pytest.mark.parametrize("passes", [True, False])
def test_runner_reports_result_and_removes_fresh_scratch(tmp_path, passes):
    source = Path(__file__).resolve().parents[1] / "scripts/run_tests.py"
    shutil.copyfile(source, tmp_path / "run_tests.py")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_example.py").write_text(
        "from pathlib import Path\n"
        "def test_example(tmp_path):\n"
        "    Path('scratch.txt').write_text(str(tmp_path.parent))\n"
        f"    assert {passes!r}\n", encoding="utf-8")
    result = subprocess.run([sys.executable, "run_tests.py"], cwd=tmp_path,
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == (0 if passes else 1), result.stdout + result.stderr
    assert ("1 passed" if passes else "1 failed") in result.stdout
    scratch = Path((tmp_path / "scratch.txt").read_text())
    assert scratch.name.startswith("showwork-pytest-")
    assert not scratch.exists()
