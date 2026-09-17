"""Submit one explicitly prepared proof JSON to an advisory endpoint.

This optional example does not inspect a repository or change a showwork ledger.
It uses only Python's standard library. No model judgment is verification.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

DEFAULT_ENDPOINT = "https://bmdpat.com/api/showwork/check-proof"
MAX_BYTES = 32 * 1024
FIELDS = {"requested_outcome", "claim", "check", "evidence"}
VERDICTS = {"appears_supported", "scope_gap", "contradicted", "insufficient_context"}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def load_input(path: Path) -> dict:
    """Read only the path the caller explicitly selected, with a byte bound."""
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("Input must be at most 32 KiB.")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict) or set(value) != FIELDS:
        raise ValueError("Input must have exactly requested_outcome, claim, check, and evidence.")
    if any(not isinstance(value[key], str) for key in FIELDS):
        raise ValueError("All four fields must be strings.")
    if not value["requested_outcome"].strip() or not value["claim"].strip():
        raise ValueError("Requested outcome and claim cannot be blank.")
    if any(len(value[key]) > (24000 if key in {"check", "evidence"} else 16000) for key in FIELDS):
        raise ValueError("A text field exceeds the endpoint limit.")
    return value


def validate_result(value: object) -> dict:
    if not isinstance(value, dict) or value.get("advisory") is not True or value.get("verdict") not in VERDICTS:
        raise ValueError("The endpoint did not return an advisory assessment.")
    confidence = value.get("confidence")
    probabilities = value.get("probabilities")
    def probability(number):
        return type(number) in {int, float} and math.isfinite(number) and 0 <= number <= 1
    if not probability(confidence) or not isinstance(probabilities, dict) or set(probabilities) != VERDICTS:
        raise ValueError("Invalid assessment probabilities.")
    if any(not probability(p) for p in probabilities.values()) or abs(sum(probabilities.values()) - 1) > 0.001:
        raise ValueError("Invalid assessment probabilities.")
    if probabilities[value["verdict"]] < max(probabilities.values()):
        raise ValueError("Assessment does not match its distribution.")
    if value.get("model") != "jev-1.13.0" or value.get("rubric_version") != "check-proof-v1":
        raise ValueError("Unexpected model or rubric version.")
    if value.get("requires_review") is not (confidence < 0.8):
        raise ValueError("Invalid review flag.")
    usage = value.get("usage")
    if not isinstance(usage, dict) or any(type(usage.get(k)) is not int or usage[k] < 0 for k in ("input_tokens", "output_tokens")):
        raise ValueError("Invalid usage result.")
    latency = value.get("latency_ms")
    if type(latency) not in {int, float} or not math.isfinite(latency) or latency < 0:
        raise ValueError("Invalid latency result.")
    # No echo of unrecognized response fields, which might contain input text.
    clean = {key: value[key] for key in ("advisory", "verdict", "confidence", "probabilities", "requires_review", "model", "rubric_version", "latency_ms")}
    clean["usage"] = {key: usage[key] for key in ("input_tokens", "output_tokens")}
    return clean


def submit(value: dict, endpoint: str = DEFAULT_ENDPOINT) -> dict:
    target = urlsplit(endpoint)
    if target.username or target.password or target.fragment:
        raise ValueError("Endpoint must not contain credentials or a fragment.")
    if target.scheme != "https" and not (target.scheme == "http" and target.hostname in {"localhost", "127.0.0.1", "::1"}):
        raise ValueError("Use HTTPS, or HTTP on a loopback host for local testing.")
    body = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(body) > MAX_BYTES:
        raise ValueError("Encoded request exceeds 32 KiB.")
    request = Request(endpoint, data=body, headers={"Content-Type": "application/json", "User-Agent": "showwork-check-proof-example/1"}, method="POST")
    try:
        with build_opener(NoRedirect()).open(request, timeout=10) as response:
            raw = response.read(64 * 1024 + 1)
            if len(raw) > 64 * 1024:
                raise ValueError("Endpoint response is too large.")
            return validate_result(json.loads(raw.decode("utf-8")))
    except HTTPError as error:
        error.close()
        raise ValueError(f"Endpoint returned HTTP {error.code}; no assessment was obtained.") from None
    except (URLError, TimeoutError):
        raise ValueError("Endpoint was unreachable or timed out; no assessment was obtained.") from None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="JSON you explicitly prepared for external assessment; omit secrets")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="Defaults to the public bmdpat endpoint; redirects are refused")
    args = parser.parse_args(argv)
    try:
        value = load_input(args.input)
        result = submit(value, args.endpoint)
    except (OSError, ValueError, UnicodeError) as error:
        # JSON parser errors and filesystem errors can echo user data or paths.
        message = str(error) if type(error) is ValueError else "Could not read input or parse the assessment."
        print(message, file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    print("Advisory text assessment only. Run showwork's deterministic checks separately.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
