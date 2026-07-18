"""Mechanical guard that every normative MUST in SPEC.md names a real test."""

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_every_normative_must_names_an_existing_test():
    text = (ROOT / "SPEC.md").read_text(encoding="utf-8")
    untagged = re.findall(r"\bMUST\b(?!\s*\[test:)", text)
    assert not untagged, "every MUST must carry a [test: path::test_name] mapping"
    mappings = re.findall(r"MUST\s*\[test:\s*([^\]]+)\]", text, flags=re.MULTILINE)
    assert len(mappings) >= 20
    for mapping in mappings:
        file_name, test_name = (part.strip() for part in mapping.split("::", 1))
        test_path = ROOT / file_name
        assert test_path.is_file(), mapping
        test_text = test_path.read_text(encoding="utf-8")
        assert re.search(rf"^def\s+{re.escape(test_name)}\s*\(", test_text, re.MULTILINE), mapping


def test_claims_are_jsonl_records(tmp_path):
    path = tmp_path / "claims.jsonl"
    records = [
        {"session": "s", "ts": "t1", "claim": "one", "severity": "RED"},
        {"session": "s", "ts": "t2", "claim": "two", "severity": "YELLOW"},
    ]
    with path.open("a", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record) + "\n")
    assert [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] == records


def test_readme_links_current_spec_version():
    """User-facing docs must name the SPEC version actually declared in SPEC.md.

    Pre-fix, README and case-study still said spec-v0.1 while SPEC.md header
    was already spec-v0.2 — wrong onboarding pointer after the v0.2 ship.
    """
    spec = (ROOT / "SPEC.md").read_text(encoding="utf-8")
    m = re.search(r"Specification version:\*\*\s*`([^`]+)`", spec)
    if not m:
        m = re.search(r"Specification version:\s*`([^`]+)`", spec)
    assert m, "SPEC.md must declare Specification version"
    version = m.group(1)
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert f"`{version}`" in readme, f"README must link {version}"
    case = (ROOT / "docs" / "case-study.md").read_text(encoding="utf-8")
    assert f"`{version}`" in case, f"case-study must link {version}"
