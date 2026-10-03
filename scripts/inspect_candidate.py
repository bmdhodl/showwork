"""Inspect local release evidence without tags, uploads or mutable state.

The caller supplies the reviewed revision and accepted-change selection. Those
inputs are observations, not independently established review or authorization.
"""

from __future__ import annotations

import argparse
from email.parser import BytesParser
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import zipfile


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bounded_bytes(path: Path, limit: int, label: str) -> bytes:
    with path.open("rb") as handle:
        data = handle.read(limit + 1)
    require(len(data) <= limit, f"{label} exceeds the read limit")
    return data


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key in gate evidence")
        result[key] = value
    return result


def inspect_candidate(root: Path, reviewed_sha: str, base_sha: str, version: str,
                      wheel: Path | None, gate: Path | None, *,
                      accepted_change: bool = False, retry_sha256: str | None = None) -> dict:
    """Return a review packet; never execute a receipt command or publish."""
    root = root.resolve()
    for sha in (reviewed_sha, base_sha):
        require(bool(re.fullmatch(r"[0-9a-f]{40}", sha)), "revision must be a full lowercase Git SHA")
    require(bool(re.fullmatch(r"\d+\.\d+\.\d+", version)), "version must be MAJOR.MINOR.PATCH")

    def git(*args):
        proc = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True,
                              timeout=30, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        require(proc.returncode == 0, "cannot validate Git revision or ancestry")
        return proc.stdout.strip()

    require(git("rev-parse", "HEAD") == reviewed_sha, "candidate is stale: HEAD differs from reviewed SHA")
    require(git("rev-parse", "origin/main") == reviewed_sha, "reviewed SHA differs from fetched origin/main")
    git("merge-base", "--is-ancestor", base_sha, reviewed_sha)
    require(not git("status", "--porcelain"), "candidate source tree must be clean")
    source = (root / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"$', source, re.MULTILINE)
    require(match is not None and match.group(1) == version, "proposed tag/version differs from source metadata")
    packet = {"reviewed_sha": reviewed_sha, "base_sha": base_sha,
              "proposed_version": version, "proposed_tag": f"v{version}",
              "publication_authorized": False,
              "selection": "caller supplied; meaningfulness and review need owner confirmation"}
    if not accepted_change or base_sha == reviewed_sha:
        require(retry_sha256 is None, "no-release selection cannot resume publication")
        return {**packet, "decision": "no-release", "artifact_checks": "not performed"}

    require(wheel is not None and wheel.is_file(), "candidate wheel is missing")
    require(wheel.suffix == ".whl" and wheel.stat().st_size <= 50 * 1024 * 1024,
            "wheel must be a bounded .whl file")
    wheel_bytes = bounded_bytes(wheel, 50 * 1024 * 1024, "wheel")
    wheel_sha = hashlib.sha256(wheel_bytes).hexdigest()
    if retry_sha256 is not None:
        require(bool(re.fullmatch(r"[0-9a-f]{64}", retry_sha256)), "retry hash must be SHA256")
        require(wheel_sha == retry_sha256, "retry must retain the exact previously approved artifact")
    with zipfile.ZipFile(io.BytesIO(wheel_bytes)) as archive:
        metadata = [item for item in archive.infolist() if item.filename.endswith(".dist-info/METADATA")]
        require(len(metadata) == 1 and metadata[0].file_size <= 256 * 1024,
                "wheel must contain one bounded package metadata file")
        fields = BytesParser().parsebytes(archive.read(metadata[0]))
    require(fields.get_all("Name") == ["showwork"] and fields.get_all("Version") == [version],
            "wheel identity differs from proposed package/version")
    require(gate is not None and gate.is_file(), "receipt gate evidence is missing")
    gate_bytes = bounded_bytes(gate, 4 * 1024 * 1024, "gate evidence")
    payload = json.loads(gate_bytes.decode("utf-8"), object_pairs_hook=unique_object)
    require(isinstance(payload, dict) and payload.get("verdict") == "GREEN"
            and payload.get("errors") == [], "receipt gate is not GREEN or contains errors")
    sessions = payload.get("sessions")
    require(isinstance(sessions, list) and bool(sessions), "receipt gate has no sessions")
    for session in sessions:
        require(isinstance(session, dict) and session.get("verdict") == "GREEN"
                and session.get("errors") == [], "session gate is not GREEN")
        checks = session.get("checks", {})
        require(isinstance(checks, dict) and checks.get("verdict") == "GREEN"
                and isinstance(checks.get("outcome"), dict)
                and checks["outcome"].get("verdict") == "VERIFIED", "acceptance outcome is not VERIFIED")
        results = checks.get("results")
        require(isinstance(results, list) and all(isinstance(row, dict) for row in results),
                "receipt results are malformed")
        behavior = [row for row in results if row.get("requirement_id") and row.get("scope") == "behavior"]
        require(bool(behavior), "candidate needs executable behavior acceptance evidence")
        for row in behavior:
            evidence = row.get("evidence")
            require(row.get("status") == "pass" and isinstance(evidence, dict)
                    and evidence.get("git_commit") == reviewed_sha
                    and type(evidence.get("exit_code")) is int
                    and evidence["exit_code"] == 0, "behavior evidence failed or names another revision")
    return {**packet, "decision": "candidate-for-owner-review", "wheel_sha256": wheel_sha,
            "gate_sha256": hashlib.sha256(gate_bytes).hexdigest(), "retry": retry_sha256 is not None,
            "limits": ["Local input hashes do not authenticate producer or prove wheel/source equivalence",
                       "No clean-install matrix, compatibility review or owner approval inferred",
                       "No receipt commands, provider queries, tags or publication executed"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--reviewed-sha", required=True)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--gate", type=Path)
    parser.add_argument("--accepted-change", action="store_true")
    parser.add_argument("--retry-sha256")
    args = parser.parse_args(argv)
    try:
        packet = inspect_candidate(args.root, args.reviewed_sha, args.base_sha, args.version,
                                   args.wheel, args.gate, accepted_change=args.accepted_change,
                                   retry_sha256=args.retry_sha256)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        parser.exit(2, f"candidate refused: {exc}\n")
    print(json.dumps(packet, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
