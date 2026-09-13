"""Refuse publication unless a version tag selects the current main commit."""

import os
from pathlib import Path
import re
import subprocess


def validate_release(root: Path, ref: str) -> str:
    match = re.fullmatch(r"refs/tags/v(\d+\.\d+\.\d+)", ref)
    if not match:
        raise ValueError("publication requires a vMAJOR.MINOR.PATCH tag")

    def git(*args: str) -> str:
        return subprocess.check_output(
            ["git", *args], cwd=root, text=True, timeout=30
        ).strip()

    head = git("rev-parse", "HEAD")
    if head != git("rev-parse", "origin/main"):
        raise ValueError("release commit must equal origin/main")
    if head != git("rev-parse", f"{ref}^{{commit}}"):
        raise ValueError("release tag must resolve to the checked-out commit")
    metadata = (root / "pyproject.toml").read_text(encoding="utf-8")
    version = re.search(r'^version = "([^"]+)"$', metadata, re.MULTILINE)
    if version is None or version.group(1) != match.group(1):
        raise ValueError("tag version must match package version")
    return head


if __name__ == "__main__":
    print(validate_release(Path.cwd(), os.environ.get("GITHUB_REF", "")))
