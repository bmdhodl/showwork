"""Evidence pack generation: content, redaction, tamper refusal."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from evidence_pack import build_pack  # noqa: E402

from showwork.ledger import (  # noqa: E402
    claims_path,
    finish_session,
    record_claim,
    start_session,
)

DAY = "2026-07-16"


def _seed(root: Path) -> None:
    start_session(root, "sess-a", agent="claude-code")
    (root / "artifact.txt").write_text("done", encoding="utf-8")
    record_claim(root, "sess-a", "wrote artifact for client-x",
                 check={"type": "file_exists", "path": "artifact.txt"})
    assert finish_session(root, "sess-a")[0] == 0


def test_pack_contains_integrity_controls_and_inventory(tmp_path):
    _seed(tmp_path)
    code, text = build_pack(tmp_path, "2026-01-01", "2026-12-31",
                            ["eu-ai-act", "soc2", "hipaa"], [])
    assert code == 0
    assert "Integrity of this evidence" in text
    assert "Art. 12 - Record-keeping" in text
    assert "CC8.1" in text
    assert "164.312(b)" in text
    assert "wrote artifact for client-x" in text
    assert "NOT legal advice" in text


def test_pack_redacts(tmp_path):
    _seed(tmp_path)
    code, text = build_pack(tmp_path, "2026-01-01", "2026-12-31",
                            ["soc2"], [r"client-\w+"])
    assert code == 0
    assert "client-x" not in text
    assert "[redacted]" in text


def test_pack_refuses_tampered_ledger(tmp_path):
    _seed(tmp_path)
    record_claim(tmp_path, "sess-a", "second claim",
                 check={"type": "file_exists", "path": "artifact.txt"})
    path = claims_path(tmp_path)
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    lines[0] = lines[0].replace("artifact", "artefact")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    code, text = build_pack(tmp_path, "2026-01-01", "2026-12-31", ["soc2"], [])
    assert code == 2
    assert "REFUSED" in text


def test_pack_date_range_filters(tmp_path):
    _seed(tmp_path)
    code, text = build_pack(tmp_path, "2020-01-01", "2020-12-31", ["soc2"], [])
    assert code == 0
    assert "Claims recorded in range: **0**" in text
