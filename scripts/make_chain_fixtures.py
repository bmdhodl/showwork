"""Regenerate the cross-implementation chain fixtures (tests/fixtures/chain/).

The fixtures freeze the spec-v0.2 integrity-chain semantics so every
implementation (Python reference, js/showwork-audit, anything future) must
produce the same verdicts on the same bytes. Deterministic on purpose: fixed
timestamps, no randomness. Rerun only when the chain semantics change, and
commit the diff consciously - these files are a conformance contract.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from showwork.ledger import genesis_hash, line_hash  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "chain"


def rec(i: int, claim: str) -> dict:
    return {"session": "fx", "ts": f"2026-07-16T00:00:0{i}", "claim": claim,
            "severity": "RED"}


def chain(path: Path, records: list[dict], start_unchained: int = 0) -> list[str]:
    """Serialize records; records[>=start_unchained] get chained `prev`."""
    lines: list[str] = []
    for i, r in enumerate(records):
        r = dict(r)
        if i >= start_unchained:
            prev = line_hash(lines[-1]) if lines else genesis_hash(path)
            r["prev"] = prev
        lines.append(json.dumps(r, ensure_ascii=False))
    return lines


def write(name: str, lines: list[str], eol: str = "\n") -> None:
    (OUT / name).write_bytes((eol.join(lines) + eol).encode("utf-8"))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    expected: dict[str, dict] = {}

    base = [rec(1, "one"), rec(2, "two"), rec(3, "three")]

    # 1. intact: fully chained
    lines = chain(OUT / "intact.jsonl", base)
    write("intact.jsonl", lines)
    expected["intact.jsonl"] = {"verdict": "GREEN", "break_at": None,
                                "chained": 3, "pre_chain": 0}

    # 2. tampered: content of record 2 altered after record 3 chained onto it
    lines = chain(OUT / "tampered.jsonl", base)
    lines[1] = lines[1].replace('"two"', '"2wo"')
    write("tampered.jsonl", lines)
    expected["tampered.jsonl"] = {"verdict": "RED", "break_at": 3}

    # 3. deleted: middle record removed from an intact chain
    lines = chain(OUT / "deleted.jsonl", base)
    del lines[1]
    write("deleted.jsonl", lines)
    expected["deleted.jsonl"] = {"verdict": "RED", "break_at": 2}

    # 4. unchained record appended after the chain started
    lines = chain(OUT / "unchained-after-start.jsonl", base[:2])
    lines.append(json.dumps(rec(3, "sneaky"), ensure_ascii=False))
    write("unchained-after-start.jsonl", lines)
    expected["unchained-after-start.jsonl"] = {"verdict": "RED", "break_at": 3}

    # 5. pre-chain record anchored by later chained appends
    lines = chain(OUT / "pre-chain-anchored.jsonl", base, start_unchained=1)
    write("pre-chain-anchored.jsonl", lines)
    expected["pre-chain-anchored.jsonl"] = {"verdict": "GREEN", "break_at": None,
                                            "chained": 2, "pre_chain": 1}

    # 6. legacy only: spec-v0.1 file, no chain at all
    lines = [json.dumps(r, ensure_ascii=False) for r in base[:2]]
    write("legacy-only.jsonl", lines)
    expected["legacy-only.jsonl"] = {"verdict": "YELLOW", "break_at": None,
                                     "chained": 0, "pre_chain": 2}

    # 7. crlf: intact chain whose file uses \r\n line endings
    lines = chain(OUT / "crlf.jsonl", base)
    write("crlf.jsonl", lines, eol="\r\n")
    expected["crlf.jsonl"] = {"verdict": "GREEN", "break_at": None}

    # 8. comments and blank lines are not records
    lines = chain(OUT / "comments.jsonl", base[:2])
    lines = ["# a comment", lines[0], "", lines[1]]
    write("comments.jsonl", lines)
    expected["comments.jsonl"] = {"verdict": "GREEN", "break_at": None,
                                  "chained": 2}

    # 9/10. forked: two concurrent branches re-anchor to the same parent line,
    #    exactly as a git union-merge of two sessions produces. The chain is
    #    intact (no tampering); it is simply not linear. `prev` is genesis-
    #    anchored per file, so each fixture is built under its own name.
    def build_forked(name: str) -> list[str]:
        target = OUT / name
        parent = dict(rec(1, "parent")); parent["prev"] = genesis_hash(target)
        p_line = json.dumps(parent, ensure_ascii=False)
        a1 = dict(rec(2, "A-one")); a1["prev"] = line_hash(p_line)
        a1_line = json.dumps(a1, ensure_ascii=False)
        b1 = dict(rec(3, "B-one")); b1["prev"] = line_hash(p_line)  # re-anchors to parent
        b1_line = json.dumps(b1, ensure_ascii=False)
        b2 = dict(rec(4, "B-two")); b2["prev"] = line_hash(b1_line)
        return [p_line, a1_line, b1_line, json.dumps(b2, ensure_ascii=False)]

    write("forked.jsonl", build_forked("forked.jsonl"))
    expected["forked.jsonl"] = {"verdict": "GREEN", "break_at": None,
                                "chained": 4, "pre_chain": 0, "forks": 1}

    # forked then tampered: altering the shared parent breaks the first record
    # that anchored to it — tamper-evidence survives forks.
    tampered_fork = build_forked("forked-tampered.jsonl")
    tampered_fork[0] = tampered_fork[0].replace('"parent"', '"p4rent"')
    write("forked-tampered.jsonl", tampered_fork)
    expected["forked-tampered.jsonl"] = {"verdict": "RED", "break_at": 2}

    # 11. hostile prev that is not a string (an object): a break, never a crash
    lines = chain(OUT / "nonstring-prev.jsonl", base[:1])
    hostile = dict(rec(2, "hostile")); hostile["prev"] = {}
    lines.append(json.dumps(hostile, ensure_ascii=False))
    write("nonstring-prev.jsonl", lines)
    expected["nonstring-prev.jsonl"] = {"verdict": "RED", "break_at": 2}

    # --- cross-implementation dialect fixtures (2026-07-17) -----------------
    # These freeze the JSON dialect and line-segmentation rules so the Python
    # reference and js/showwork-audit stay bound on hostile/degenerate input.
    # Each was a real divergence before the fix; the bytes are written raw
    # because json.dumps cannot emit them.

    # 12. bare NaN is not valid JSON. json.loads used to accept it (making the
    #     record a live one with a float `prev` -> RED); JSON.parse rejects it.
    #     Now both treat the line as unparseable: one pre-chain record, YELLOW.
    nonfinite = ('{"session": "fx", "ts": "2026-07-16T00:00:01", '
                 '"claim": "nonfinite", "severity": "RED", "prev": NaN}')
    (OUT / "nonfinite-constant.jsonl").write_bytes((nonfinite + "\n").encode("utf-8"))
    expected["nonfinite-constant.jsonl"] = {"verdict": "YELLOW", "break_at": None,
                                            "chained": 0, "pre_chain": 1}

    # 13. a raw U+2028 inside a JSON string is part of that string, not a line
    #     break. str.splitlines() split it (cutting the JSON in two -> RED);
    #     \r?\n keeps the record whole, so the chain stays intact (GREEN).
    target = OUT / "u2028-in-string.jsonl"
    a = dict(rec(1, "one")); a["prev"] = genesis_hash(target)
    a_line = json.dumps(a, ensure_ascii=False)
    b = dict(rec(2, "line\u2028break")); b["prev"] = line_hash(a_line)
    b_line = json.dumps(b, ensure_ascii=False)  # ensure_ascii=False keeps U+2028 raw
    (OUT / "u2028-in-string.jsonl").write_bytes((a_line + "\n" + b_line + "\n").encode("utf-8"))
    expected["u2028-in-string.jsonl"] = {"verdict": "GREEN", "break_at": None,
                                         "chained": 2, "pre_chain": 0}

    # 14. a lone CR is not a record separator under \r?\n: the whole file is one
    #     physical line (invalid JSON -> one unparseable pre-chain record,
    #     YELLOW). str.splitlines() would have split it into two chained records.
    target = OUT / "lone-cr.jsonl"
    a = dict(rec(1, "one")); a["prev"] = genesis_hash(target)
    a_line = json.dumps(a, ensure_ascii=False)
    b = dict(rec(2, "two")); b["prev"] = line_hash(a_line)
    b_line = json.dumps(b, ensure_ascii=False)
    (OUT / "lone-cr.jsonl").write_bytes((a_line + "\r" + b_line + "\n").encode("utf-8"))
    expected["lone-cr.jsonl"] = {"verdict": "YELLOW", "break_at": None,
                                 "chained": 0, "pre_chain": 1}

    # 15. break_at line numbering: records separated by \n\r, with record 2
    #     tampered so record 3's prev dangles. splitlines() counts the stray CR
    #     as its own blank line and reports the break at line 5; \r?\n reports
    #     it at line 3, matching the JS auditor.
    target = OUT / "nlcr-break-numbering.jsonl"
    a = dict(rec(1, "one")); a["prev"] = genesis_hash(target)
    a_line = json.dumps(a, ensure_ascii=False)
    b = dict(rec(2, "two")); b["prev"] = line_hash(a_line)
    b_line = json.dumps(b, ensure_ascii=False)
    c = dict(rec(3, "three")); c["prev"] = line_hash(b_line)
    c_line = json.dumps(c, ensure_ascii=False)
    b_tampered = b_line.replace('"two"', '"2wo"')  # record 3's prev no longer resolves
    (OUT / "nlcr-break-numbering.jsonl").write_bytes(
        (a_line + "\n\r" + b_tampered + "\n\r" + c_line + "\n").encode("utf-8"))
    expected["nlcr-break-numbering.jsonl"] = {"verdict": "RED", "break_at": 3}

    (OUT / "expected.json").write_text(
        json.dumps(expected, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(expected)} fixtures + expected.json to {OUT}")


if __name__ == "__main__":
    main()
