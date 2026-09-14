"""Publication provenance checked against actual Git refs."""

import importlib.util
from pathlib import Path
import subprocess
import shlex

import pytest

spec = importlib.util.spec_from_file_location(
    "validate_release", Path(__file__).parents[1] / "scripts/validate_release.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture
def repo(tmp_path):
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=tmp_path, text=True).strip()
    git("init", "-b", "main")
    git("config", "user.email", "fixture@example.invalid")
    git("config", "user.name", "Fixture")
    (tmp_path / "pyproject.toml").write_text('version = "0.5.0"\n')
    git("add", ".")
    git("commit", "-m", "baseline")
    git("update-ref", "refs/remotes/origin/main", "HEAD")
    git("tag", "v0.5.0")
    return tmp_path, git


def test_release_accepts_main_version_tag(repo):
    root, git = repo
    assert module.validate_release(root, "refs/tags/v0.5.0") == git("rev-parse", "HEAD")


@pytest.mark.parametrize("ref", ["refs/heads/main", "", "refs/tags/vbad"])
def test_release_refuses_non_release_refs(repo, ref):
    with pytest.raises(ValueError, match="requires"):
        module.validate_release(repo[0], ref)


def test_release_refuses_unreviewed_branch_commit(repo):
    root, git = repo
    git("commit", "--allow-empty", "-m", "off-main")
    with pytest.raises(ValueError, match="origin/main"):
        module.validate_release(root, "refs/tags/v0.5.0")


def test_release_refuses_version_mismatch(repo):
    root, git = repo
    git("tag", "v9.9.9")
    with pytest.raises(ValueError, match="package version"):
        module.validate_release(root, "refs/tags/v9.9.9")


def test_publisher_fetch_handles_checkout_peeled_annotated_tag(repo):
    # REGRESSION: checkout peels an annotated tag into a local lightweight tag.
    # Fetching --tags then refuses to replace it, before provenance can run.
    root, git = repo
    git("tag", "-f", "-a", "v0.5.0", "-m", "annotated release")
    remote = root.parent / (root.name + "-origin.git")
    subprocess.run(["git", "clone", "--bare", str(root), str(remote)], check=True,
                   capture_output=True)
    git("remote", "add", "origin", str(remote))
    git("tag", "-f", "v0.5.0", "HEAD")
    workflow = (Path(__file__).parents[1] / ".github/workflows/publish.yml").read_text()
    fetch = next(line.strip() for line in workflow.splitlines() if line.strip().startswith("git fetch "))
    result = subprocess.run(shlex.split(fetch), cwd=root, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert module.validate_release(root, "refs/tags/v0.5.0") == git("rev-parse", "HEAD")
