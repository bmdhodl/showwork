"""Codex records one handoff. A later process must not share this memory.

The command check stores its timeout on the finish event. This script does
not grant a later session permission to close.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


TIMEOUT_SECONDS = "30"
REPO = Path(__file__).resolve().parents[2]


def child_env() -> dict[str, str]:
    env = os.environ.copy()
    src = REPO / "src"
    if (src / "showwork" / "__init__.py").is_file():
        prev = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = str(src) + (os.pathsep + prev if prev else "")
    env.pop("SHOWWORK_ROOT", None)
    env.pop("SHOWWORK_SESSION", None)
    env["SHOWWORK_COMMAND_TIMEOUT_SECONDS"] = TIMEOUT_SECONDS
    return env


def git(root: Path, *args: str) -> None:
    proc = subprocess.run(
        ["git", *args], cwd=root, text=True, capture_output=True, check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "git failed").strip()
        raise SystemExit(detail)


def showwork(root: Path, *args: str) -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "showwork.cli", "--root", str(root), *args],
        cwd=root, env=child_env(), text=True, capture_output=True, check=False,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "showwork failed").strip()
        raise SystemExit(f"{' '.join(args)}\n{detail}")


def write_tree(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "note.txt").write_bytes(b"ready\n")
    (root / "check.py").write_bytes(b"print('passed')\n")
    (root / "DECISION.md").write_text(
        "\n".join([
            "# Note text",
            "",
            "The note file must contain ready.",
            "The command check limit is the timeout on the finish event.",
            "This file is the governing decision.",
            "A model summary is not a decision.",
            "",
        ]),
        encoding="utf-8",
    )
    git(root, "init", "-b", "main")
    git(root, "add", "note.txt", "check.py", "DECISION.md")
    git(
        root, "-c", "user.name=showwork", "-c", "user.email=showwork@example.com",
        "commit", "-m", "fixture",
    )
    showwork(root, "start", "--session", "handoff", "--agent", "codex")
    showwork(
        root, "require", "--session", "handoff", "--id", "note",
        "--scope", "artifact", "--description", "note.txt contains ready",
        "--type", "file_contains", "--path", "note.txt", "--pattern", "ready",
    )
    showwork(
        root, "require", "--session", "handoff", "--id", "run",
        "--scope", "behavior", "--description", "check.py exits 0 and prints passed",
        "--type", "command", "--command-arg", "python", "--command-arg", "check.py",
        "--expect-exit", "0", "--stdout-contains", "passed",
    )
    showwork(
        root, "claim", "--session", "handoff", "--claim", "note.txt exists",
        "--type", "file_exists", "--path", "note.txt",
    )
    showwork(
        root, "claim", "--session", "handoff", "--claim", "check.py exists",
        "--type", "file_exists", "--path", "check.py",
    )
    showwork(root, "finish", "--session", "handoff", "--status", "ok")
    showwork(root, "start", "--session", "fileonly", "--agent", "codex")
    showwork(
        root, "require", "--session", "fileonly", "--id", "note",
        "--scope", "artifact", "--description", "note.txt contains ready",
        "--type", "file_contains", "--path", "note.txt", "--pattern", "ready",
    )
    showwork(
        root, "claim", "--session", "fileonly", "--claim", "note.txt exists",
        "--type", "file_exists", "--path", "note.txt",
    )
    showwork(root, "finish", "--session", "fileonly", "--status", "ok")
    # The pointer is not part of the code snapshot. A later supersede must
    # stay visible even when the receipt is still green.
    (root / "decision.json").write_text(
        "\n".join([
            "{",
            '  "id": "note-text",',
            '  "source": "DECISION.md",',
            '  "session": "handoff",',
            '  "superseded_by": null',
            "}",
            "",
        ]),
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("usage: write_codex.py <directory>", file=sys.stderr)
        return 2
    write_tree(Path(args[0]).resolve())
    print(args[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
