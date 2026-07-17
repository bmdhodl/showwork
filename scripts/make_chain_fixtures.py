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

    (OUT / "expected.json").write_text(
        json.dumps(expected, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(expected)} fixtures + expected.json to {OUT}")


if __name__ == "__main__":
    main()
