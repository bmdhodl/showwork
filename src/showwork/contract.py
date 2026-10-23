"""Detect an obvious test command and write an honest default contract.

``showwork init`` uses this so a new repository can close through ``finish``
without a handwritten ``require`` / ``claim``. A vacuous contract is worse
than none: if nothing is detected, nothing is written.
"""

from __future__ import annotations

import json
import re
import shlex
from dataclasses import dataclass
from pathlib import Path

CONTRACT_REL = ".showwork/contract.json"
RUNNER_REL = ".showwork/run_default_check.py"
CONTRACT_VERSION = 1
DEFAULT_REQUIREMENT_ID = "tests"
DEFAULT_DESCRIPTION = "the project test command must pass"
NO_COMMAND_NOTE = (
    "no obvious test command (looked for pytest, npm test, go test, cargo test); "
    "no default contract written"
)

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
_PYTEST_FILE = re.compile(r"(?:^|/)test_[^/]+\.py$|(?:^|/).+_test\.py$")


@dataclass(frozen=True)
class DetectedCommand:
    argv: tuple[str, ...]
    source: str


def detect_test_command(root: Path) -> DetectedCommand | None:
    """Return the first obvious test command, or None.

    Order is the first honest match, not a scored ranking: a project-local
    runner, then pytest markers, then ``npm test``, then Go, then Cargo.
    """
    root = root.resolve()
    if not root.is_dir():
        return None
    runner = root / "scripts" / "run_tests.py"
    if runner.is_file():
        return DetectedCommand(("python", "scripts/run_tests.py"), "scripts/run_tests.py")
    if (root / "pytest.ini").is_file() or _setup_cfg_has_pytest(root) or _pyproject_has_pytest(root):
        return DetectedCommand(_pytest_argv(root), _pytest_source(root))
    if _has_pytest_files(root / "tests"):
        return DetectedCommand(_pytest_argv(root), "tests/")
    npm = _npm_test(root)
    if npm is not None:
        return npm
    if (root / "go.mod").is_file():
        return DetectedCommand(("go", "test", "./..."), "go.mod")
    if (root / "Cargo.toml").is_file():
        return DetectedCommand(("cargo", "test"), "Cargo.toml")
    return None


def _pytest_argv(root: Path) -> tuple[str, ...]:
    if (root / "tests").is_dir():
        return ("python", "-m", "pytest", "tests")
    return ("python", "-m", "pytest")


def _pytest_source(root: Path) -> str:
    if (root / "pytest.ini").is_file():
        return "pytest.ini"
    if _setup_cfg_has_pytest(root):
        return "setup.cfg"
    return "pyproject.toml"


def _setup_cfg_has_pytest(root: Path) -> bool:
    text = _read_text(root / "setup.cfg")
    return text is not None and "[tool:pytest]" in text


def _pyproject_has_pytest(root: Path) -> bool:
    text = _read_text(root / "pyproject.toml")
    return text is not None and "[tool.pytest" in text


def _has_pytest_files(tests_dir: Path) -> bool:
    if not tests_dir.is_dir():
        return False
    try:
        for path in tests_dir.rglob("*.py"):
            relative = path.relative_to(tests_dir).as_posix()
            if _PYTEST_FILE.search(relative):
                return True
    except OSError:
        return False
    return False


def _npm_test(root: Path) -> DetectedCommand | None:
    path = root / "package.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        return None
    if not isinstance(data, dict):
        return None
    scripts = data.get("scripts")
    if not isinstance(scripts, dict):
        return None
    test = scripts.get("test")
    if isinstance(test, str) and test.strip():
        return DetectedCommand(("npm", "test"), "package.json scripts.test")
    return None


def _read_text(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


def render_contract(detected: DetectedCommand) -> str:
    payload = {
        "version": CONTRACT_VERSION,
        "test_command": list(detected.argv),
        "detected_from": detected.source,
    }
    return json.dumps(payload, indent=2) + "\n"


def runner_text() -> str:
    return (_TEMPLATE_DIR / "run_default_check.py").read_text(encoding="utf-8")


def default_check() -> dict:
    return {"type": "command", "argv": ["python", RUNNER_REL], "expect_exit": 0}


def load_contract(root: Path) -> dict | None:
    path = root.resolve() / CONTRACT_REL
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError) as exc:
        raise ValueError(f"{CONTRACT_REL} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{CONTRACT_REL} must contain a JSON object")
    if data.get("version") != CONTRACT_VERSION:
        raise ValueError(f"{CONTRACT_REL} version must be {CONTRACT_VERSION}")
    command = data.get("test_command")
    if not isinstance(command, list) or not command or not all(isinstance(item, str) for item in command):
        raise ValueError(f"{CONTRACT_REL} test_command must be a non-empty list of strings")
    return data


def write_default_contract(root: Path, *, force: bool = False, preview: bool = False) -> list[str]:
    """Write or skip the default contract. Never invents a command."""
    root = root.resolve()
    detected = detect_test_command(root)
    if detected is None:
        return [NO_COMMAND_NOTE]
    notes = [
        _write_generated(root, CONTRACT_REL, render_contract(detected), force, preview),
        _write_generated(root, RUNNER_REL, runner_text(), force, preview),
        (
            f"default contract: {shlex.join(detected.argv)} must pass at finish "
            f"(requirement id: {DEFAULT_REQUIREMENT_ID}). Edit {CONTRACT_REL} to change it."
        ),
    ]
    return notes


def uninstall_default_contract(root: Path, *, preview: bool = False) -> list[str]:
    """Remove only unchanged generated contract files."""
    root = root.resolve()
    notes: list[str] = []
    detected = detect_test_command(root)
    expected = {
        CONTRACT_REL: render_contract(detected) if detected is not None else None,
        RUNNER_REL: runner_text(),
    }
    for relative, text in expected.items():
        dest = root / relative
        if not dest.is_file():
            continue
        current = dest.read_text(encoding="utf-8")
        if text is None or current != text:
            notes.append(f"keep {relative} (edited)")
            continue
        notes.append(f"{'would remove' if preview else 'remove'} {relative}")
        if not preview:
            dest.unlink()
    return notes


def apply_default_contract(root: Path, session: str) -> dict | None:
    """Declare the init contract on a started session that has no claims yet."""
    contract = load_contract(root)
    if contract is None:
        return None
    runner = root.resolve() / RUNNER_REL
    if not runner.is_file():
        raise ValueError(
            f"{CONTRACT_REL} exists but {RUNNER_REL} is missing; re-run showwork init"
        )
    from .ledger import _latest_session_start, claims_for_session
    from .outcomes import record_requirement, requirement_records

    if not _latest_session_start(root, session):
        return None
    if any(row.get("requirement_id") == DEFAULT_REQUIREMENT_ID
           for row in requirement_records(root, session)):
        return None
    if claims_for_session(root, session):
        return None
    return record_requirement(
        root, session, DEFAULT_REQUIREMENT_ID, DEFAULT_DESCRIPTION,
        "behavior", default_check(),
    )


def _write_generated(root: Path, relative: str, text: str, force: bool, preview: bool) -> str:
    dest = root / relative
    if dest.is_file() and not force:
        return f"skip {relative} (exists; pass --force)"
    if preview:
        return f"would write {relative}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    return f"write {relative}"
