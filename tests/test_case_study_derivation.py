"""The public case-study derivation emits aggregates, not private claim data."""

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "derive_case_study.py"
SPEC = importlib.util.spec_from_file_location("derive_case_study", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_derivation_is_aggregate_and_reproducible(tmp_path):
    vault = tmp_path / "vault"
    claims = vault / "Reports" / "Claims"
    state = vault / "Reports" / "State"
    claims.mkdir(parents=True)
    state.mkdir(parents=True)
    private_claim = "private strategy secret"
    rows = [
        {"session": "s1", "claim": private_claim,
         "check": {"type": "file_exists", "path": "secret.txt"}},
        {"session": "s2", "claim": "plain prose"},
        {"session": "s1", "retracted": True,
         "retracts": {"session": "s1", "claim": private_claim}},
    ]
    ledger = claims / "2026-06-20.jsonl"
    ledger.write_text("\n".join(json.dumps(row) for row in rows) + "\n{bad json\n",
                      encoding="utf-8")
    (claims / "claims-audit-2026-06-20.md").write_text(
        "**Verdict: GREEN** (1/2 verified)\n", encoding="utf-8")
    (state / "state-audit-2026-06-20.md").write_text("state", encoding="utf-8")
    (vault / "log.md").write_text(
        "two claimed actions were NOT actually done\n", encoding="utf-8")

    metrics = MODULE.derive(vault)

    assert metrics["total_claims_recorded"] == 2
    assert metrics["verifiable_claims_recorded"] == 1
    assert metrics["retraction_records"] == 1
    assert metrics["malformed_ledger_lines"] == 1
    assert metrics["documented_origin_false_dones"] == 2
    assert private_claim not in json.dumps(metrics)
    assert metrics == MODULE.derive(vault)
