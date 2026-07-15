"""Derive sanitized showwork case-study metrics from the production vault.

The output contains aggregates and source fingerprints only. It never copies
claim text, paths, strategy, financial data, or trading data into the public
repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date
from pathlib import Path


CLAIM_FILE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.jsonl$")
AUDIT_SUMMARY = re.compile(r"\*\*Verdict:\s*(RED|YELLOW|GREEN)\*\*\s*\((\d+)/(\d+) verified\)")
ORIGIN_SENTENCE = "two claimed actions were NOT actually done"


def _records(path: Path) -> tuple[list[dict], int]:
    records: list[dict] = []
    parse_errors = 0
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            parse_errors += 1
            continue
        if isinstance(value, dict):
            records.append(value)
    return records, parse_errors


def derive(vault: Path) -> dict:
    claims_dir = vault / "Reports" / "Claims"
    files = sorted(
        path for path in claims_dir.glob("*.jsonl") if CLAIM_FILE.match(path.name)
    )
    if not files:
        raise ValueError(f"no dated claims ledgers found under {claims_dir}")

    all_records: list[dict] = []
    parse_errors = 0
    digest = hashlib.sha256()
    for path in files:
        payload = path.read_bytes()
        digest.update(path.name.encode("ascii"))
        digest.update(b"\0")
        digest.update(payload)
        records, file_errors = _records(path)
        all_records.extend(records)
        parse_errors += file_errors

    claims = [record for record in all_records if not record.get("retracts")]
    retractions = [record for record in all_records if record.get("retracted")]
    dated = [CLAIM_FILE.match(path.name).group(1) for path in files]
    first = date.fromisoformat(dated[0])
    last = date.fromisoformat(dated[-1])

    latest_audit = claims_dir / f"claims-audit-{dated[-1]}.md"
    audit_match = AUDIT_SUMMARY.search(latest_audit.read_text(encoding="utf-8-sig")) \
        if latest_audit.is_file() else None

    log_lines = (vault / "log.md").read_text(encoding="utf-8-sig").splitlines()
    origin_line = next((index for index, line in enumerate(log_lines, 1)
                        if ORIGIN_SENTENCE in line), None)
    if origin_line is None:
        raise ValueError("origin false-done evidence is missing from log.md")

    state_reports = sorted((vault / "Reports" / "State").glob("state-audit-*.md"))
    return {
        "schema": "showwork-case-study-metrics-v1",
        "source": "sanitized aggregates from the private production vault",
        "ledger_files": len(files),
        "malformed_ledger_lines": parse_errors,
        "total_claims_recorded": len(claims),
        "verifiable_claims_recorded": sum(isinstance(record.get("check"), dict)
                                          for record in claims),
        "unique_sessions": len({str(record.get("session", "")) for record in claims
                                if record.get("session")}),
        "retraction_records": len(retractions),
        "documented_origin_false_dones": 2,
        "origin_evidence": f"log.md:{origin_line}",
        "first_ledger_date": dated[0],
        "last_ledger_date": dated[-1],
        "calendar_span_days": (last - first).days + 1,
        "active_ledger_days": len(set(dated)),
        "state_audit_reports": len(state_reports),
        "latest_audit": ({
            "verdict": audit_match.group(1),
            "passed": int(audit_match.group(2)),
            "total": int(audit_match.group(3)),
        } if audit_match else None),
        "claims_source_sha256": digest.hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--output", type=Path,
                        default=Path("docs/case-study-metrics.json"))
    args = parser.parse_args()
    metrics = derive(args.vault.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
