"""showwork: falsifiable claims and deterministic verification for AI agents.

Make your agents show their work. Observability logs what an agent did;
showwork verifies what it CLAIMED it did, and refuses to bless a "done"
that is not backed by reality.
"""

from .audit import audit_file, audit_root, render_audit
from .checks import CHECKERS, evaluate_records, render_report, verify_claim
from .hooks import observe_stop, payload_session_id, read_stop_payload
from .ledger import (
    claims_for_session,
    finish_session,
    load_claims,
    record_claim,
    record_event,
    record_retraction,
    resolve_root,
    start_session,
    verify_date,
    verify_session,
)

__version__ = "0.2.0"

__all__ = [
    "CHECKERS",
    "audit_file",
    "audit_root",
    "claims_for_session",
    "evaluate_records",
    "finish_session",
    "load_claims",
    "observe_stop",
    "payload_session_id",
    "record_claim",
    "record_event",
    "record_retraction",
    "read_stop_payload",
    "render_audit",
    "render_report",
    "resolve_root",
    "start_session",
    "verify_claim",
    "verify_date",
    "verify_session",
    "__version__",
]
