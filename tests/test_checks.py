"""Behavioral tests for the deterministic checkers and verdict logic."""

import json

import pytest

from showwork.checks import evaluate_records, verify_claim


def claim(check=None, severity="RED", **extra):
    rec = {"session": "t", "claim": extra.pop("text", "test claim"), "severity": severity}
    if check is not None:
        rec["check"] = check
    rec.update(extra)
    return rec


# ---------- file_exists ----------

def test_file_exists_pass(tmp_path):
    (tmp_path / "a.txt").write_text("hi", encoding="utf-8")
    r = verify_claim(claim({"type": "file_exists", "path": "a.txt"}), tmp_path)
    assert r["status"] == "pass"


def test_file_exists_fail(tmp_path):
    r = verify_claim(claim({"type": "file_exists", "path": "missing.txt"}), tmp_path)
    assert r["status"] == "fail"


def test_file_exists_directory_is_not_missing(tmp_path):
    """A present directory must fail as not-a-file, not as 'missing'.

    SPEC: pass only when path is a regular file. Pre-fix used only is_file(),
    so a directory produced detail 'd missing' — false and misleading when
    agents debug path_moved / wrong check type mistakes.
    """
    (tmp_path / "d").mkdir()
    r = verify_claim(claim({"type": "file_exists", "path": "d"}), tmp_path)
    assert r["status"] == "fail"
    assert "missing" not in r["detail"]
    assert "regular file" in r["detail"] or "not a file" in r["detail"].lower()


def test_file_checks_reject_evidence_outside_project_root(tmp_path):
    outside = tmp_path.parent / "outside-proof.txt"
    outside.write_text("secret proof", encoding="utf-8")
    checks = [
        {"type": "file_exists", "path": "../outside-proof.txt"},
        {"type": "file_contains", "path": "../outside-proof.txt", "pattern": "secret"},
        {"type": "frontmatter", "path": "../outside-proof.txt", "field": "status", "equals": "done"},
    ]
    for check in checks:
        result = verify_claim(claim(check), tmp_path)
        assert result["status"] == "fail"
        assert "escapes project root" in result["detail"]


def test_path_args_must_be_strings(tmp_path):
    """Non-string path fields must not raise TypeError from Path join.

    Pre-fix, path/from/to of None or int produced
    'checker raised: unsupported operand type(s) for /: WindowsPath and NoneType'.
    """
    cases = [
        {"type": "file_exists", "path": None},
        {"type": "file_contains", "path": 1, "pattern": "x"},
        {"type": "frontmatter", "path": None, "field": "a", "equals": "b"},
        {"type": "path_moved", "from": None, "to": "a.txt"},
        {"type": "path_moved", "from": "a.txt", "to": 2},
    ]
    for check in cases:
        r = verify_claim(claim(check), tmp_path)
        assert r["status"] == "error", check
        assert "checker raised" not in r["detail"], r
        assert "string" in r["detail"].lower() or "path" in r["detail"].lower(), r


# ---------- file_contains ----------

def test_file_contains_pass_and_fail(tmp_path):
    (tmp_path / "a.md").write_text("alpha beta", encoding="utf-8")
    ok = verify_claim(claim({"type": "file_contains", "path": "a.md", "pattern": "beta"}), tmp_path)
    bad = verify_claim(claim({"type": "file_contains", "path": "a.md", "pattern": "gamma"}), tmp_path)
    assert ok["status"] == "pass"
    assert bad["status"] == "fail"


def test_file_contains_absent(tmp_path):
    (tmp_path / "a.md").write_text("alpha", encoding="utf-8")
    r = verify_claim(claim({"type": "file_contains", "path": "a.md",
                            "pattern": "gamma", "absent": True}), tmp_path)
    assert r["status"] == "pass"


def test_file_contains_rejects_vacuous_pattern(tmp_path):
    """A regex matching the empty string proves nothing; it must error, not pass."""
    (tmp_path / "a.md").write_text("anything", encoding="utf-8")
    for pattern in ("", ".*", "^", "x?"):
        r = verify_claim(claim({"type": "file_contains", "path": "a.md",
                                "pattern": pattern}), tmp_path)
        assert r["status"] == "error", pattern


def test_file_contains_invalid_regex_errors(tmp_path):
    (tmp_path / "a.md").write_text("x", encoding="utf-8")
    r = verify_claim(claim({"type": "file_contains", "path": "a.md", "pattern": "("}), tmp_path)
    assert r["status"] == "error"


def test_file_contains_pattern_must_be_string(tmp_path):
    """Non-string pattern must error clearly, not re.error/TypeError noise."""
    (tmp_path / "a.md").write_text("x", encoding="utf-8")
    for bad in (None, ["x"], 12):
        r = verify_claim(claim({"type": "file_contains", "path": "a.md", "pattern": bad}),
                         tmp_path)
        assert r["status"] == "error", bad
        assert "checker raised" not in r["detail"], r
        assert "pattern" in r["detail"].lower(), r


def test_file_contains_bom_safe(tmp_path):
    (tmp_path / "a.md").write_bytes(b"\xef\xbb\xbfneedle here")
    r = verify_claim(claim({"type": "file_contains", "path": "a.md", "pattern": "needle"}), tmp_path)
    assert r["status"] == "pass"


def test_file_contains_directory_is_not_missing(tmp_path):
    """A directory must not be reported as a missing file for file_contains."""
    (tmp_path / "d").mkdir()
    r = verify_claim(claim({"type": "file_contains", "path": "d", "pattern": "x"}), tmp_path)
    assert r["status"] == "fail"
    assert "missing" not in r["detail"]
    assert "regular file" in r["detail"] or "not a file" in r["detail"].lower()


# ---------- path_moved ----------

def test_path_moved(tmp_path):
    (tmp_path / "done").mkdir()
    (tmp_path / "done" / "t.md").write_text("x", encoding="utf-8")
    ok = verify_claim(claim({"type": "path_moved", "from": "t.md", "to": "done/t.md"}), tmp_path)
    assert ok["status"] == "pass"
    (tmp_path / "t.md").write_text("still here", encoding="utf-8")
    bad = verify_claim(claim({"type": "path_moved", "from": "t.md", "to": "done/t.md"}), tmp_path)
    assert bad["status"] == "fail"


def test_path_moved_rejects_evidence_outside_project_root(tmp_path):
    result = verify_claim(
        claim({"type": "path_moved", "from": "../before.md", "to": "done.md"}),
        tmp_path,
    )
    assert result["status"] == "fail"
    assert "escapes project root" in result["detail"]


def test_path_moved_rejects_empty_paths(tmp_path):
    """Empty from/to must not pass by resolving to the project root.

    Pre-fix, Path(root / '') is the root directory, so a claim that a
    missing source was 'moved' to '' passed whenever the project root existed
    — a vacuous false proof.
    """
    # Source gone, empty destination → must NOT pass
    r = verify_claim(claim({"type": "path_moved", "from": "gone.md", "to": ""}),
                     tmp_path)
    assert r["status"] in ("fail", "error")
    assert r["status"] != "pass"
    # Empty source / empty both
    for check in (
        {"type": "path_moved", "from": "", "to": "done.md"},
        {"type": "path_moved", "from": "", "to": ""},
    ):
        r = verify_claim(claim(check), tmp_path)
        assert r["status"] in ("fail", "error"), check
        assert r["status"] != "pass", check


# ---------- frontmatter ----------

def test_frontmatter(tmp_path):
    (tmp_path / "task.md").write_text("---\nstatus: done\n---\nbody", encoding="utf-8")
    ok = verify_claim(claim({"type": "frontmatter", "path": "task.md",
                             "field": "status", "equals": "done"}), tmp_path)
    bad = verify_claim(claim({"type": "frontmatter", "path": "task.md",
                              "field": "status", "equals": "pending"}), tmp_path)
    missing = verify_claim(claim({"type": "frontmatter", "path": "task.md",
                                  "field": "nope", "equals": "x"}), tmp_path)
    assert ok["status"] == "pass"
    assert bad["status"] == "fail"
    assert missing["status"] == "fail"


def test_frontmatter_no_block(tmp_path):
    (tmp_path / "plain.md").write_text("no frontmatter", encoding="utf-8")
    r = verify_claim(claim({"type": "frontmatter", "path": "plain.md",
                            "field": "status", "equals": "done"}), tmp_path)
    assert r["status"] == "fail"


def test_frontmatter_json_bool_equals_yaml_true(tmp_path):
    """--check-json booleans must match YAML true/false scalars.

    JSON true becomes Python True; str(True) is 'True', which never equals the
    frontmatter scalar 'true'. Agents using --check-json with equals:true then
    get a permanent RED fail despite a correct file.
    """
    (tmp_path / "task.md").write_text("---\npublished: true\n---\nbody", encoding="utf-8")
    ok = verify_claim(claim({"type": "frontmatter", "path": "task.md",
                             "field": "published", "equals": True}), tmp_path)
    assert ok["status"] == "pass", ok
    bad = verify_claim(claim({"type": "frontmatter", "path": "task.md",
                              "field": "published", "equals": False}), tmp_path)
    assert bad["status"] == "fail"
    # String form still works (CLI --equals always passes strings).
    assert verify_claim(claim({"type": "frontmatter", "path": "task.md",
                               "field": "published", "equals": "true"}),
                        tmp_path)["status"] == "pass"


# ---------- glob_count ----------

def test_glob_count(tmp_path):
    for i in range(3):
        (tmp_path / f"n{i}.md").write_text("x", encoding="utf-8")
    ok = verify_claim(claim({"type": "glob_count", "pattern": "*.md", "op": "==", "n": 3}), tmp_path)
    bad = verify_claim(claim({"type": "glob_count", "pattern": "*.md", "op": ">", "n": 5}), tmp_path)
    assert ok["status"] == "pass"
    assert bad["status"] == "fail"


def test_glob_count_rejects_vacuous(tmp_path):
    """count >= 0 is always true; it must error, not pass."""
    r = verify_claim(claim({"type": "glob_count", "pattern": "*.md", "op": ">=", "n": 0}), tmp_path)
    assert r["status"] == "error"


def test_glob_count_rejects_escape(tmp_path):
    outside = tmp_path.parent / "outside.md"
    outside.write_text("x", encoding="utf-8")
    r = verify_claim(
        claim({"type": "glob_count", "pattern": "../*.md", "op": ">=", "n": 1}),
        tmp_path,
    )
    assert r["status"] == "fail"
    assert "escapes project root" in r["detail"]
    r = verify_claim(claim({"type": "glob_count", "pattern": "*.md", "op": ">", "n": -1}), tmp_path)
    assert r["status"] == "error"


def test_glob_count_rejects_empty_pattern(tmp_path):
    """Empty glob pattern must be a clear error, not a pathlib traceback phrase.

    Pre-fix, pattern '' became WindowsPath('.') and raised
    'Unacceptable pattern', wrapped as 'checker raised: ...'.
    """
    r = verify_claim(claim({"type": "glob_count", "pattern": "", "op": ">=", "n": 1}), tmp_path)
    assert r["status"] == "error"
    assert "checker raised" not in r["detail"]
    assert "pattern" in r["detail"].lower()


# ---------- command (locked) ----------

def test_command_happy_path(tmp_path):
    (tmp_path / "ok.py").write_text("print('all good')", encoding="utf-8")
    r = verify_claim(claim({"type": "command", "argv": ["python", "ok.py"],
                            "stdout_contains": "all good"}), tmp_path)
    assert r["status"] == "pass"


def test_command_exit_code_mismatch(tmp_path):
    (tmp_path / "boom.py").write_text("raise SystemExit(2)", encoding="utf-8")
    r = verify_claim(claim({"type": "command", "argv": ["python", "boom.py"]}), tmp_path)
    assert r["status"] == "fail"


def test_command_stdout_contains_requires_string(tmp_path):
    """Non-string stdout_contains must error clearly, not raise TypeError.

    Pre-fix, needle and `not in proc.stdout` with an int left operand
    produced: checker raised: 'in <string>' requires string as left operand.
    """
    (tmp_path / "ok.py").write_text("print('hi')", encoding="utf-8")
    r = verify_claim(claim({"type": "command", "argv": ["python", "ok.py"],
                            "stdout_contains": 1}), tmp_path)
    assert r["status"] == "error"
    assert "checker raised" not in r["detail"]
    assert "stdout_contains" in r["detail"]


def test_command_lock_rejects_shell_meta(tmp_path):
    r = verify_claim(claim({"type": "command", "argv": ["python", "a.py;rm"]}), tmp_path)
    assert r["status"] == "error"


def test_command_lock_rejects_non_python(tmp_path):
    r = verify_claim(claim({"type": "command", "argv": ["bash", "x.sh"]}), tmp_path)
    assert r["status"] == "error"


def test_command_lock_rejects_powershell(tmp_path):
    r = verify_claim(claim({"type": "command", "argv": ["python", "x.ps1"]}), tmp_path)
    assert r["status"] == "error"


def test_command_lock_rejects_escape(tmp_path):
    r = verify_claim(claim({"type": "command", "argv": ["python", "../outside.py"]}), tmp_path)
    assert r["status"] == "error"


def test_command_recursion_guard(tmp_path, monkeypatch):
    monkeypatch.setenv("SHOWWORK_VERIFYING", "1")
    (tmp_path / "ok.py").write_text("print('x')", encoding="utf-8")
    r = verify_claim(claim({"type": "command", "argv": ["python", "ok.py"]}), tmp_path)
    assert r["status"] == "error"
    assert "recursion" in r["detail"]


# ---------- skips, retractions, verdicts ----------

def test_no_check_is_skipped(tmp_path):
    r = verify_claim(claim(None, text="squishy prose, no check"), tmp_path)
    assert r["status"] == "skipped"


def test_unknown_type_errors(tmp_path):
    r = verify_claim(claim({"type": "telepathy"}), tmp_path)
    assert r["status"] == "error"


def test_non_dict_check_is_error_not_crash(tmp_path):
    """Hostile check values must not AttributeError in verify_claim.

    A ledger can hold check as a string/array/number. Pre-fix, verify_claim
    called check.get without ensuring check is a dict.
    """
    for bad in ("file_exists", ["file_exists"], 42, True):
        rec = {"session": "t", "claim": "bad check shape", "severity": "RED",
               "check": bad}
        r = verify_claim(rec, tmp_path)
        assert r["status"] == "error", bad
        assert "object" in r["detail"].lower(), r


def test_inline_retraction_skipped(tmp_path):
    rec = claim({"type": "file_exists", "path": "missing.txt"})
    rec["retracted"] = True
    rec["retraction_reason"] = "was wrong"
    r = verify_claim(rec, tmp_path)
    assert r["status"] == "skipped"


def test_append_only_retraction(tmp_path):
    bad = claim({"type": "file_exists", "path": "missing.txt"}, text="I made a file")
    retraction = {"session": "t", "retracted": True,
                  "retracts": {"session": "t", "claim": "I made a file"},
                  "retraction_reason": "never happened"}
    state = evaluate_records([bad, retraction], tmp_path, label="t")
    assert state["verdict"] == "GREEN"
    assert state["total"] == 1  # the retraction marker itself is not a claim
    assert state["results"][0]["status"] == "skipped"


def test_reclaim_after_retraction_is_active(tmp_path):
    """A later re-claim with the same text must be verified, not left skipped.

    Retraction is append-only suppression of *prior* targets. If an agent
    retracts a false claim, fixes reality, and records the same claim text
    again, that new record is a live claim — not permanently killed by the
    earlier retraction. Otherwise finish can GREEN without ever checking the
    re-asserted outcome.
    """
    bad = claim({"type": "file_exists", "path": "a.txt"}, text="I made a file")
    retraction = {"session": "t", "retracted": True,
                  "retracts": {"session": "t", "claim": "I made a file"},
                  "retraction_reason": "never happened"}
    # Reality is fixed; agent re-asserts the same claim text.
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    reclaimed = claim({"type": "file_exists", "path": "a.txt"}, text="I made a file")
    state = evaluate_records([bad, retraction, reclaimed], tmp_path, label="t")
    assert state["total"] == 2  # original + re-claim; marker is not a claim
    assert state["results"][0]["status"] == "skipped"
    assert state["results"][1]["status"] == "pass"
    assert state["verdict"] == "GREEN"
    assert state["passed"] == 1

    # Re-claim that still fails must keep the exit gate RED.
    still_missing = claim(
        {"type": "file_exists", "path": "still-missing.txt"}, text="I made a file"
    )
    red = evaluate_records([bad, retraction, still_missing], tmp_path, label="t")
    assert red["results"][1]["status"] == "fail"
    assert red["verdict"] == "RED"


def test_verdict_red_yellow_green(tmp_path):
    (tmp_path / "real.txt").write_text("x", encoding="utf-8")
    good = claim({"type": "file_exists", "path": "real.txt"})
    red_fail = claim({"type": "file_exists", "path": "nope.txt"})
    yellow_fail = claim({"type": "file_exists", "path": "nope.txt"}, severity="YELLOW")
    assert evaluate_records([good], tmp_path)["verdict"] == "GREEN"
    assert evaluate_records([good, yellow_fail], tmp_path)["verdict"] == "YELLOW"
    assert evaluate_records([good, red_fail], tmp_path)["verdict"] == "RED"


def test_invalid_severity_on_fail_is_red_not_yellow(tmp_path):
    """Invalid/empty severity must not demote a failed claim out of RED.

    SPEC allows only RED|YELLOW. Pre-fix, severity '' or 'GREEN' became a
    non-RED label, so a failed claim produced YELLOW and finish --status ok
    could close over a real gap without refusal.
    """
    for sev in ("", "GREEN", "blue", None):
        rec = {"session": "t", "claim": "gap", "check": {"type": "file_exists",
                                                          "path": "nope.txt"}}
        if sev is not None:
            rec["severity"] = sev
        else:
            # omit key — defaults should stay RED
            pass
        state = evaluate_records([rec], tmp_path)
        assert state["verdict"] == "RED", (sev, state)
        assert state["results"][0]["severity"] == "RED", sev


def test_checker_error_is_yellow(tmp_path):
    err = claim({"type": "glob_count", "pattern": "*.md", "op": ">=", "n": 0})
    assert evaluate_records([err], tmp_path)["verdict"] == "YELLOW"


def test_records_roundtrip_json(tmp_path):
    """Claim records are plain JSON - the ledger format is the API."""
    rec = claim({"type": "file_exists", "path": "a.txt"})
    assert json.loads(json.dumps(rec)) == rec


def test_command_disabled_by_no_commands_env(tmp_path, monkeypatch):
    """CI fork-safety: SHOWWORK_NO_COMMANDS makes command checks refuse to
    execute repo code and report an error (verdict degrades to YELLOW)."""
    from showwork.checks import NO_COMMANDS_ENV, chk_command
    script = tmp_path / "ok.py"
    script.write_text("raise SystemExit(0)\n", encoding="utf-8")
    check = {"type": "command", "argv": ["python", "ok.py"]}
    monkeypatch.setenv(NO_COMMANDS_ENV, "1")
    status, detail = chk_command(check, tmp_path)
    assert status == "error"
    assert "SHOWWORK_NO_COMMANDS" in detail
    monkeypatch.delenv(NO_COMMANDS_ENV)
    status, _ = chk_command(check, tmp_path)
    assert status == "pass"
