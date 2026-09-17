import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("docs_checker", ROOT / "scripts/check_docs.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def test_documentation_links():
    errors = []
    for name in checker.DOCS:
        path = ROOT / name
        if path.exists():
            errors.extend(checker.check_file(path, repository="showwork"))
    assert errors == []


def test_readme_python_floor_matches_package_metadata():
    import re
    metadata = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    floor = re.search(r'requires-python = ">=([0-9.]+)"', metadata).group(1)
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert f"Python {floor} or newer" in readme


@pytest.mark.parametrize("link", ["[missing](gone.md)", "[heading](other.md#gone)",
                                  "![](other.md)"])
def test_broken_documentation_is_rejected(tmp_path, link):
    (tmp_path / "other.md").write_text("# Existing\n", encoding="utf-8")
    path = tmp_path / "README.md"
    path.write_text("# Test\n" + link, encoding="utf-8")
    assert checker.check_file(path, root=tmp_path)


def test_valid_heading_and_code_example_link_are_accepted(tmp_path):
    (tmp_path / "other.md").write_text("# Existing\n", encoding="utf-8")
    path = tmp_path / "README.md"
    path.write_text("# Test\n[heading](other.md#existing)\n"
                    "```python\n# [example](not-a-real-link)\n```\n", encoding="utf-8")
    assert checker.check_file(path, root=tmp_path) == []

@pytest.mark.parametrize("link", ['[guide](missing.md "Guide")',
                                  "![image](missing.png 'Diagram')"])
def test_link_titles_do_not_hide_missing_targets(tmp_path, link):
    # REGRESSION: a Markdown title made the whole link invisible to the checker.
    path = tmp_path / "README.md"
    path.write_text("# Test\n" + link, encoding="utf-8")
    assert checker.check_file(path, root=tmp_path)


@pytest.mark.parametrize("fence", ["~~~~", "````", "~~~", "   ```"])
def test_all_fenced_examples_are_ignored(tmp_path, fence):
    # REGRESSION: valid alternative fences exposed example links to validation.
    path = tmp_path / "README.md"
    path.write_text("# Test\n" + fence + "text\n[example](missing.md)\n"
                    + fence + "\n", encoding="utf-8")
    assert checker.check_file(path, root=tmp_path) == []


def test_missing_entry_points_fail(tmp_path):
    # REGRESSION: deleting a curated document silently skipped its checks.
    assert checker.check_documents(tmp_path, "showwork")


def test_current_entry_points_exist_and_pass():
    assert checker.check_documents(ROOT, "showwork") == []


def test_readme_commands_execute_as_documented(tmp_path):
    import os
    import re
    import shlex
    import subprocess
    import sys
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    env.pop("SHOWWORK_ROOT", None)
    env.pop("SHOWWORK_SESSION", None)
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    section = text.split("## Quickstart", 1)[1].split("## How it works", 1)[0]
    refusals = 0
    verified = 0
    for block in re.findall(r"```bash\n(.*?)```", section, re.S):
        for line in block.strip().splitlines():
            args = shlex.split(line)
            if args[:4] == ["python", "-m", "pip", "install"]:
                continue  # Installation is covered by packaging tests.
            if args[0] == "showwork":
                args = [sys.executable, "-m", "showwork", "--root", str(tmp_path), *args[1:]]
            elif args[0] == "python":
                args[0] = sys.executable
            else:
                raise AssertionError(f"Unrecognized quickstart command: {line}")
            result = subprocess.run(args, cwd=tmp_path, env=env, text=True,
                                    capture_output=True, timeout=30)
            expected = 2 if "finish" in args and not (tmp_path / "config/api.yaml").exists() else 0
            assert result.returncode == expected, result.stdout + result.stderr
            refusals += "REFUSED" in result.stderr
            verified += "Outcome: VERIFIED" in result.stdout
    assert refusals == 1
    assert verified == 1


def test_python_quickstart_executes(tmp_path):
    import os
    import re
    import subprocess
    import sys
    text = (ROOT / "docs/quickstart-python.md").read_text(encoding="utf-8")
    code = re.findall(r"```python\n(.*?)```", text, re.S)[0]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    env.pop("SHOWWORK_ROOT", None)
    env.pop("SHOWWORK_SESSION", None)
    result = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, env=env,
                            text=True, capture_output=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "REFUSED" in result.stdout
    assert "Outcome: VERIFIED" in result.stdout
