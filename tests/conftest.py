import importlib.metadata
import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]

# The test gate must exercise this checkout, even when another clone has been
# installed editable in the interpreter.  pytest's `pythonpath = ["src"]`
# setting does not guarantee precedence over an existing editable finder.
_LOCAL_SRC = str(ROOT / "src")
if _LOCAL_SRC in sys.path:
    sys.path.remove(_LOCAL_SRC)
sys.path.insert(0, _LOCAL_SRC)


@pytest.fixture(autouse=True)
def _clear_verifying_env(monkeypatch):
    # Tests must behave identically whether or not the suite is itself running
    # under a showwork `command` claim (dogfooding runs it exactly that way).
    # Recursion stays bounded: these tests spawn only tiny leaf scripts.
    monkeypatch.delenv("SHOWWORK_VERIFYING", raising=False)
    monkeypatch.delenv("SHOWWORK_SESSION", raising=False)
    monkeypatch.delenv("SHOWWORK_ROOT", raising=False)
    # Isolated tests use temporary leaf scripts and loopback HTTP fixtures.
    # Individual policy tests set these explicitly. The caller's policy still
    # controls whether it can launch this trusted acceptance command at all.
    monkeypatch.delenv("SHOWWORK_NO_NETWORK", raising=False)
    monkeypatch.delenv("SHOWWORK_NO_COMMANDS", raising=False)


@pytest.fixture
def slow_child_start(tmp_path, monkeypatch):
    """Make every child Python sleep before it runs any code.

    Under `showwork finish` the suite shares the host with the verifier and
    the virus scanner, and a child interpreter took longer to start than some
    budgets that counted its start-up. A `sitecustomize` on PYTHONPATH runs
    at interpreter start, so this reproduces that host on demand.
    """
    def apply(seconds: float) -> None:
        shim = tmp_path / "slow-child-start"
        shim.mkdir(exist_ok=True)
        (shim / "sitecustomize.py").write_text(
            f"import time\ntime.sleep({seconds!r})\n", encoding="utf-8")
        inherited = os.environ.get("PYTHONPATH")
        monkeypatch.setenv(
            "PYTHONPATH", os.pathsep.join(filter(None, [str(shim), inherited])))
    return apply


def _host_satisfies_build_requires() -> bool:
    try:
        import tomllib
    except ModuleNotFoundError:  # Python 3.10: test-only backport.
        import tomli as tomllib
    from packaging.requirements import Requirement  # `build` depends on it.

    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    for spec in pyproject["build-system"]["requires"]:
        requirement = Requirement(spec)
        try:
            installed = importlib.metadata.version(requirement.name)
        except importlib.metadata.PackageNotFoundError:
            return False
        if not requirement.specifier.contains(installed, prereleases=True):
            return False
    return True


@pytest.fixture
def build_dist():
    """Build this checkout's sdist or wheel, offline when the host can.

    An isolated build first makes a venv and asks the package index for
    setuptools. Under `showwork finish` that index wait pushed the sdist test
    past its 120 s limit. When this interpreter already satisfies
    [build-system] requires, build without isolation and with the index
    switched off, so a return to a network build fails at once. CI's test
    venv has no setuptools and keeps the isolated build.
    """
    def build(kind: str, outdir: Path) -> Path:
        env = os.environ.copy()
        env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
        argv = [sys.executable, "-m", "build", f"--{kind}", "--outdir", str(outdir)]
        if _host_satisfies_build_requires():
            argv.append("--no-isolation")
            env["PIP_NO_INDEX"] = "1"
        built = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True,
                               text=True, timeout=120)
        assert built.returncode == 0, built.stdout + built.stderr
        suffix = ".tar.gz" if kind == "sdist" else ".whl"
        archives = sorted(outdir.glob(f"showwork-*{suffix}"))
        assert len(archives) == 1, archives
        return archives[0]
    return build
