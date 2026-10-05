"""The source distribution must carry the files README links to."""

from __future__ import annotations

import tarfile
try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10: test-only backport, no runtime dependency.
    import tomli as tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_sdist_contains_readme_targets(tmp_path, build_dist):
    sdist = build_dist("sdist", tmp_path / "dist")
    with tarfile.open(sdist, "r:gz") as archive:
        version = tomllib.loads(
            (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )["project"]["version"]
        root = f"showwork-{version}"
        names = {name.removeprefix(root + "/") for name in archive.getnames()}

    required = {
        "llms.txt",
        "docs/README.md",
        "docs/quickstart-python.md",
        "docs/quickstart-behavior.md",
        "docs/pilot.md",
        "docs/handoff.md",
        "docs/reports/sw-04-pilot/README.md",
        "CONTRIBUTING.md",
        "SPEC.md",
        "docs/claude-code.md",
        "docs/walks/cursor.md",
        "docs/ci.md",
        "docs/adapters.md",
        "docs/false-done-rate.md",
        "docs/compliance.md",
        "docs/case-study.md",
        "scripts/evidence_pack.py",
        "js/showwork-audit/index.mjs",
    }
    assert required <= names
    assert not any("__pycache__" in name or name.endswith((".pyc", ".pyo"))
                       for name in names)
