"""Integrity-chain behavior: append hashing, tamper detection, era handling."""

import json
from pathlib import Path

from showwork.audit import audit_file, audit_root
from showwork.cli import main
from showwork.ledger import (
    claims_path,
    genesis_hash,
    line_hash,
    record_claim,
    record_event,
)


def _claims_file(root: Path) -> Path:
    return next((root / ".showwork").glob("claims-*.jsonl"))


def _lines(path: Path) -> list[str]:
    return [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_append_adds_prev_hash(tmp_path):
    record_claim(tmp_path, "s", "first",
                 check={"type": "file_exists", "path": "x"})
    record_claim(tmp_path, "s", "second",
                 check={"type": "file_exists", "path": "x"})
    path = _claims_file(tmp_path)
    first, second = (json.loads(l) for l in _lines(path))
    assert first["prev"] == genesis_hash(path)
    assert second["prev"] == line_hash(_lines(path)[0])


def test_audit_green_on_untampered_ledger(tmp_path):
    record_claim(tmp_path, "s", "one")
    record_event(tmp_path, "session.start", "s")
    state = audit_root(tmp_path)
    assert state["verdict"] == "GREEN"
    assert state["total_chained"] == state["total_records"] == 2


def test_tamper_detected_at_exact_line(tmp_path):
    record_claim(tmp_path, "s", "one")
    record_claim(tmp_path, "s", "two")
    record_claim(tmp_path, "s", "three")
    path = _claims_file(tmp_path)
    lines = _lines(path)
    lines[1] = lines[1].replace('"two"', '"2wo"')  # single-byte content change
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = audit_file(path)
    assert result["verdict"] == "RED"
    assert result["break_at"] == 3  # the record AFTER the tampered line breaks
    assert "chain break" in result["detail"]


def test_deleted_line_is_detected(tmp_path):
    record_claim(tmp_path, "s", "one")
    record_claim(tmp_path, "s", "two")
    record_claim(tmp_path, "s", "three")
    path = _claims_file(tmp_path)
    lines = _lines(path)
    del lines[1]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = audit_file(path)
    assert result["verdict"] == "RED"


def test_chain_survives_eol_rewrite(tmp_path):
    record_claim(tmp_path, "s", "one")
    record_claim(tmp_path, "s", "two")
    path = _claims_file(tmp_path)
    crlf = path.read_text(encoding="utf-8").replace("\n", "\r\n")
    path.write_bytes(crlf.encode("utf-8"))
    assert audit_file(path)["verdict"] == "GREEN"


def test_pre_chain_records_are_anchored(tmp_path):
    ledger = tmp_path / ".showwork"
    ledger.mkdir()
    path = ledger / "claims-2026-01-01.jsonl"
    path.write_text(
        json.dumps({"session": "old", "ts": "t", "claim": "legacy", "severity": "RED"}) + "\n",
        encoding="utf-8")
    record_claim(tmp_path, "s", "new")
    daily = claims_path(tmp_path)
    legacy = audit_file(path)
    assert legacy["verdict"] == "YELLOW"  # no chain in the legacy-only file
    fresh = audit_file(daily)
    assert fresh["verdict"] == "GREEN"
    # a chained append into the legacy file anchors the pre-chain record
    with path.open("a", encoding="utf-8") as f:
        rec = {"session": "s2", "ts": "t2", "claim": "chained",
               "prev": line_hash(path.read_text(encoding="utf-8").splitlines()[0])}
        f.write(json.dumps(rec) + "\n")
    anchored = audit_file(path)
    assert anchored["verdict"] == "GREEN"
    assert anchored["pre_chain"] == 1
    # tampering with the pre-chain record now breaks the chain
    lines = _lines(path)
    lines[0] = lines[0].replace("legacy", "1egacy")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert audit_file(path)["verdict"] == "RED"


def test_unchained_after_chain_start_is_red(tmp_path):
    record_claim(tmp_path, "s", "one")
    path = _claims_file(tmp_path)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"session": "s", "ts": "t", "claim": "sneaky"}) + "\n")
    result = audit_file(path)
    assert result["verdict"] == "RED"
    assert "unchained record" in result["detail"]


def test_head_hash_reported(tmp_path):
    record_claim(tmp_path, "s", "one")
    path = _claims_file(tmp_path)
    result = audit_file(path)
    assert result["head"] == line_hash(_lines(path)[-1])


def test_audit_yellow_when_nothing_to_audit(tmp_path):
    assert audit_root(tmp_path)["verdict"] == "YELLOW"


def test_cli_audit_exit_codes(tmp_path, capsys):
    record_claim(tmp_path, "s", "one")
    record_claim(tmp_path, "s", "two")
    assert main(["--root", str(tmp_path), "audit"]) == 0
    out = capsys.readouterr().out
    assert "showwork audit  =>  GREEN" in out
    # tampering with history AFTER it has been chained onto is what breaks
    path = _claims_file(tmp_path)
    lines = _lines(path)
    lines[0] = lines[0].replace("one", "0ne")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert main(["--root", str(tmp_path), "audit"]) == 2


def test_cli_audit_json(tmp_path, capsys):
    record_claim(tmp_path, "s", "one")
    assert main(["--root", str(tmp_path), "audit", "--json"]) == 0
    state = json.loads(capsys.readouterr().out)
    assert state["verdict"] == "GREEN"
    assert state["files"][0]["chained"] == 1


# ---------- concurrent-append forks (the 2026-07-16 bmdpat incident) ----------


def _sessions_file(root: Path) -> Path:
    return root / ".showwork" / "sessions.jsonl"


def _union_merge_fork(root: Path) -> Path:
    """Reproduce the exact shape git union-merge produced in bmdpat: a shared
    parent line, then two blocks (sessions B and A) that both chain off that
    same parent because each was written from a worktree holding the pre-merge
    copy. Returns the sessions.jsonl path."""
    record_event(root, "session.start", "shared")   # parent, chained off genesis
    path = _sessions_file(root)
    parent_hash = line_hash(_lines(path)[-1])
    # Session B's finish reached main first, chaining off the parent.
    b1 = {"event": "session.finish", "session": "B", "ts": "t", "prev": parent_hash}
    b1_line = json.dumps(b1)
    # Session A's worktree appended Stop-hook heartbeats chaining off the SAME
    # parent. git union-merge concatenates both blocks after the parent.
    a1 = {"event": "session.heartbeat", "session": "A", "ts": "t", "prev": parent_hash}
    a1_line = json.dumps(a1)
    a2 = {"event": "session.heartbeat", "session": "A", "ts": "t2",
          "prev": line_hash(a1_line)}
    with path.open("a", encoding="utf-8") as f:
        f.write(b1_line + "\n" + a1_line + "\n" + json.dumps(a2) + "\n")
    return path


def test_concurrent_merge_audits_green_with_forks(tmp_path):
    path = _union_merge_fork(tmp_path)
    result = audit_file(path)
    assert result["verdict"] == "GREEN"       # a linear walk went RED here
    assert result["forks"] == 1               # one block re-anchors to the parent
    assert len(result["heads"]) == 2          # session B tip and session A tip
    assert result["break_at"] is None


def test_fork_does_not_hide_tampering(tmp_path):
    path = _union_merge_fork(tmp_path)
    lines = _lines(path)
    lines[0] = lines[0].replace("shared", "sh4red")  # tamper the shared parent
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = audit_file(path)
    assert result["verdict"] == "RED"
    assert result["break_at"] == 2  # first record that anchored to the parent


def test_strict_forbids_forks(tmp_path):
    path = _union_merge_fork(tmp_path)
    assert audit_file(path)["verdict"] == "GREEN"
    strict = audit_file(path, strict=True)
    assert strict["verdict"] == "RED"
    assert "fork" in strict["detail"]


def test_two_genesis_roots_is_a_fork_not_a_break(tmp_path):
    record_event(tmp_path, "session.start", "A")  # anchored to genesis
    path = _sessions_file(tmp_path)
    second = {"event": "session.start", "session": "B", "ts": "t",
              "prev": genesis_hash(path)}  # a second independent root
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(second) + "\n")
    result = audit_file(path)
    assert result["verdict"] == "GREEN"
    assert result["forks"] == 1


def test_cli_audit_strict_exit_code(tmp_path, capsys):
    _union_merge_fork(tmp_path)
    assert main(["--root", str(tmp_path), "audit"]) == 0
    capsys.readouterr()
    assert main(["--root", str(tmp_path), "audit", "--strict"]) == 2


def test_audit_file_missing_or_directory_is_yellow_not_crash(tmp_path):
    """audit_file must not raise FileNotFoundError/PermissionError on bad paths.

    The public auditor is called with ledger paths that may be missing or a
    directory. Pre-fix, read_record_text raised; callers (and mistaken CLI
    paths) crashed instead of getting a YELLOW unprovable result.
    """
    missing = audit_file(tmp_path / "no-such.jsonl")
    assert missing["verdict"] == "YELLOW"
    assert "not a ledger file" in missing["detail"] or "missing" in missing["detail"].lower()

    directory = audit_file(tmp_path)
    assert directory["verdict"] == "YELLOW"
    assert "not a ledger file" in directory["detail"] or "directory" in directory["detail"].lower()


# ---------- cross-implementation dialect: framing must match js/showwork-audit ----------


def test_line_boundaries_are_lf_or_crlf_only(tmp_path):
    # str.splitlines() breaks on U+2028 and a lone CR; a JSON.parse-based reader
    # (js/showwork-audit) does not. Splitting on \r?\n keeps the two in step.
    ledger = tmp_path / ".showwork"
    ledger.mkdir()
    path = ledger / "claims-2026-01-01.jsonl"
    r1 = {"session": "s", "ts": "t", "claim": "one", "prev": genesis_hash(path)}
    l1 = json.dumps(r1, ensure_ascii=False)
    # a raw U+2028 sits inside record 2's JSON string; it is not a line break
    r2 = {"session": "s", "ts": "t", "claim": "a\u2028b", "prev": line_hash(l1)}
    l2 = json.dumps(r2, ensure_ascii=False)
    path.write_bytes((l1 + "\n" + l2 + "\n").encode("utf-8"))
    intact = audit_file(path)
    assert intact["records"] == 2       # U+2028 stayed inside record 2
    assert intact["verdict"] == "GREEN"
    # a lone CR is not a separator: one physical line, which is invalid JSON, so
    # a single unparseable pre-chain record — never two chained records.
    path.write_bytes((l1 + "\r" + l2 + "\n").encode("utf-8"))
    lone_cr = audit_file(path)
    assert lone_cr["records"] == 1
    assert lone_cr["verdict"] == "YELLOW"


def test_nonstandard_json_constants_are_parse_errors(tmp_path):
    # json.loads accepts bare NaN/Infinity/-Infinity; JSON.parse rejects them.
    # The reader must too, so such a line is an unparseable pre-chain record
    # (YELLOW), never a live record whose `prev` is a float.
    ledger = tmp_path / ".showwork"
    ledger.mkdir()
    path = ledger / "claims-2026-01-01.jsonl"
    for literal in ("NaN", "Infinity", "-Infinity"):
        line = '{"session": "s", "ts": "t", "claim": "x", "prev": ' + literal + "}"
        path.write_bytes((line + "\n").encode("utf-8"))
        result = audit_file(path)
        assert result["records"] == 1, literal
        assert result["chained"] == 0, literal
        assert result["pre_chain"] == 1, literal
        assert result["verdict"] == "YELLOW", literal


def test_ledger_reader_rejects_nonfinite_constants(tmp_path):
    # The verification reader (_read_jsonl) shares the strict dialect: a bare
    # Infinity becomes the visible unparseable placeholder, not a live record.
    from showwork.ledger import load_claims
    ledger = tmp_path / ".showwork"
    ledger.mkdir()
    (ledger / "claims-2026-01-01.jsonl").write_bytes(
        b'{"session": "s", "ts": "t", "claim": "x", "value": Infinity}\n')
    records = load_claims(tmp_path, "2026-01-01")
    assert len(records) == 1
    assert records[0]["severity"] == "YELLOW"
    assert "_parse_error" in records[0]


def test_non_string_prev_is_a_break_not_a_crash(tmp_path):
    # A hostile ledger must report, never raise: numbers, objects, and arrays
    # in prev are all breaks (unhashable values would crash a naive set lookup).
    for bad_prev in (12345, {}, ["x"]):
        record_claim(tmp_path, "s", "one")
        path = _claims_file(tmp_path)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"session": "s", "ts": "t", "claim": "x",
                                "prev": bad_prev}) + "\n")
        result = audit_file(path)
        assert result["verdict"] == "RED", bad_prev
        assert result["break_at"] == 2, bad_prev
        path.unlink()
