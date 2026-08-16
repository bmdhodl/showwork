"""The source distribution must carry the files README links to."""

from __future__ import annotations

import subprocess
import sys
import tarfile
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_sdist_contains_readme_targets(tmp_path):
    out = tmp_path / "dist"
    out.mkdir()
    subprocess.run(
        [sys.executable, "-m", "build", "--sdist", "--outdir", str(out)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    archives = sorted(out.glob("showwork-*.tar.gz"))
    assert len(archives) == 1
    with tarfile.open(archives[0], "r:gz") as archive:
        version = tomllib.loads(
            (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )["project"]["version"]
        root = f"showwork-{version}"
        names = {name.removeprefix(root + "/") for name in archive.getnames()}

    required = {
        "SPEC.md",
        "docs/claude-code.md",
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
