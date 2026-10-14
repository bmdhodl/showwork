"""tests_intact: static comparison of Python tests against a pinned base commit."""

import subprocess

import pytest

from showwork.checks import validate_check_shape, verify_claim
from showwork.tests_intact import scan_source

BASE = """\
import pytest
import unittest


def test_plain():
    assert 1 + 1 == 2
    assert 2 * 2 == 4


@pytest.mark.parametrize("n", [1, 2, 3])
def test_cases(n):
    assert n > 0


def test_raises():
    with pytest.raises(ZeroDivisionError):
        1 / 0


class TestGroup:
    def test_member(self):
        assert True


class Legacy(unittest.TestCase):
    def test_equal(self):
        self.assertEqual(1, 1)


def helper():
    assert False
"""


def _repo(tmp_path, source=BASE, name="tests/test_mod.py"):
    root = tmp_path / "repo"
    (root / name).parent.mkdir(parents=True)
    (root / name).write_text(source, encoding="utf-8")
    for args in (["init", "-q"], ["config", "user.email", "t@example.com"],
                 ["config", "user.name", "t"], ["add", "-A"], ["commit", "-qm", "base"]):
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], check=True,
                          capture_output=True, text=True).stdout.strip()
    return root, head


def _check(root, base, path="tests"):
    return verify_claim({"session": "s", "claim": "tests intact",
                         "check": {"type": "tests_intact", "path": path, "base": base}}, root)


def test_scan_counts_tests_assertions_skips_and_cases():
    tests = scan_source(BASE)
    assert sorted(tests) == ["Legacy::test_equal", "TestGroup::test_member", "test_cases",
                             "test_plain", "test_raises"]
    assert tests["test_plain"] == {"asserts": 2, "skips": 0, "cases": 1}
    assert tests["test_cases"]["cases"] == 3
    assert tests["test_raises"]["asserts"] == 1
    assert tests["Legacy::test_equal"]["asserts"] == 1


def test_unchanged_and_strengthened_tests_pass(tmp_path):
    root, base = _repo(tmp_path)
    assert _check(root, base)["status"] == "pass"
    (root / "tests" / "test_mod.py").write_text(
        BASE.replace("[1, 2, 3]", "[1, 2, 3, 4]") + "\n\ndef test_new():\n    assert 3\n",
        encoding="utf-8")
    (root / "tests" / "test_other.py").write_text("def test_x():\n    assert 1\n", encoding="utf-8")
    result = _check(root, base)
    assert result["status"] == "pass", result["detail"]
    assert "5 tests and 6 assertions in 1 test file(s)" in result["detail"]


@pytest.mark.parametrize("edit, finding", [
    (lambda s: s.replace("    assert 2 * 2 == 4\n", ""),
     "assertions fell from 2 to 1: tests/test_mod.py::test_plain"),
    (lambda s: s.replace("def test_plain", "@pytest.mark.xfail\ndef test_plain"),
     "test newly skipped or xfail: tests/test_mod.py::test_plain"),
    (lambda s: s.replace("    def test_equal(self):\n",
                         "    @unittest.skip('later')\n    def test_equal(self):\n"),
     "test newly skipped or xfail: tests/test_mod.py::Legacy::test_equal"),
    (lambda s: s.replace("        assert True", "        pytest.skip('flaky')\n        assert True"),
     "test newly skipped or xfail: tests/test_mod.py::TestGroup::test_member"),
    (lambda s: s.replace("class TestGroup:", "@pytest.mark.skip\nclass TestGroup:"),
     "test newly skipped or xfail: tests/test_mod.py::TestGroup::test_member"),
    (lambda s: s.replace("import unittest\n", "import unittest\npytestmark = pytest.mark.skip\n"),
     "test newly skipped or xfail: tests/test_mod.py::test_plain"),
    (lambda s: s.replace("[1, 2, 3]", "[1]"),
     "parametrize cases fell from 3 to 1: tests/test_mod.py::test_cases"),
    (lambda s: s.replace("    with pytest.raises(ZeroDivisionError):\n        1 / 0\n", "    pass\n"),
     "assertions fell from 1 to 0: tests/test_mod.py::test_raises"),
    (lambda s: s.replace("def test_raises", "def check_raises"),
     "test deleted: tests/test_mod.py::test_raises"),
    (lambda s: s + "\ndef broken(:\n", "tests/test_mod.py no longer parses"),
])
def test_weakened_tests_fail_with_the_reason(tmp_path, edit, finding):
    root, base = _repo(tmp_path)
    path = root / "tests" / "test_mod.py"
    path.write_text(edit(BASE), encoding="utf-8")
    result = _check(root, base)
    assert result["status"] == "fail"
    assert finding in result["detail"]


def test_deleted_test_file_fails(tmp_path):
    root, base = _repo(tmp_path)
    (root / "tests" / "test_mod.py").unlink()
    result = _check(root, base)
    assert result["status"] == "fail"
    assert "test file deleted: tests/test_mod.py (5 tests)" in result["detail"]


def test_base_is_read_from_git_not_the_worktree(tmp_path):
    root, base = _repo(tmp_path)
    path = root / "tests" / "test_mod.py"
    path.write_text(BASE.replace("    assert 2 * 2 == 4\n", ""), encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "commit", "-qam", "weaken"], check=True, capture_output=True)
    assert _check(root, base)["status"] == "fail"


def test_no_tests_at_base_is_an_error_not_a_pass(tmp_path):
    root, base = _repo(tmp_path, source="x = 1\n", name="src/mod.py")
    result = _check(root, base, path="src")
    assert result["status"] == "error"
    assert "would prove nothing" in result["detail"]
    root2, base2 = _repo(tmp_path / "b", source="def helper():\n    pass\n")
    assert _check(root2, base2)["status"] == "error"


def test_unknown_base_commit_is_an_error(tmp_path):
    root, _ = _repo(tmp_path)
    result = _check(root, "0" * 40)
    assert result["status"] == "error"


def test_tests_intact_shape_is_validated(tmp_path):
    assert validate_check_shape({"type": "tests_intact", "path": "tests", "base": "a" * 40}, tmp_path) is None
    assert "full lowercase commit" in validate_check_shape(
        {"type": "tests_intact", "path": "tests", "base": "HEAD"}, tmp_path)
    assert "full lowercase commit" in validate_check_shape(
        {"type": "tests_intact", "path": "tests", "base": "abc1234"}, tmp_path)
    assert "non-empty" in validate_check_shape({"type": "tests_intact", "base": "a" * 40}, tmp_path)
    assert "under the project root" in validate_check_shape(
        {"type": "tests_intact", "path": "../tests", "base": "a" * 40}, tmp_path)
    assert "does not accept" in validate_check_shape(
        {"type": "tests_intact", "path": "tests", "base": "a" * 40, "min": 3}, tmp_path)


def test_cli_pins_the_base_as_a_full_commit(tmp_path, capsys):
    import json
    from showwork.cli import main
    root, head = _repo(tmp_path)
    assert main(["--root", str(root), "start", "--session", "pin"]) == 0
    assert main(["--root", str(root), "require", "--session", "pin", "--id", "intact",
                 "--scope", "artifact", "--description", "intact", "--type", "tests_intact",
                 "--path", "tests"]) == 0
    events = (root / ".showwork" / "sessions" / "pin.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(events[-1])["check"] == {"type": "tests_intact", "path": "tests", "base": head}
    assert main(["--root", str(root), "claim", "--session", "pin", "--claim", "x",
                 "--type", "tests_intact", "--path", "tests", "--commit", "no-such-rev"]) == 2
    assert "cannot resolve" in capsys.readouterr().err
