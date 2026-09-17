"""The opt-in client cannot turn a remote model judgment into verification."""
import importlib.util
import io
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_proof_example", ROOT / "examples/check_proof.py")
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)


def result():
    return {"advisory": True, "verdict": "scope_gap", "confidence": 0.9,
            "probabilities": {key: 0.97 if key == "scope_gap" else 0.01 for key in client.VERDICTS},
            "requires_review": False, "model": "jev-1.13.0", "rubric_version": "check-proof-v1",
            "usage": {"input_tokens": 100, "output_tokens": 10}, "latency_ms": 100}


def test_only_explicit_input_is_sent_to_real_loopback_http(tmp_path, capsys, monkeypatch):
    # REGRESSION: a configured proxy must never receive a loopback submission.
    monkeypatch.setenv("http_proxy", "http://127.0.0.1:1")
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("NO_PROXY", "")
    monkeypatch.setenv("no_proxy", "")
    submitted = []
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            submitted.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({**result(), "unexpected_private_echo": "NEVER_PRINT"}).encode())
        def log_message(self, *_args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    selected = tmp_path / "selected.json"
    original = client.load_input(ROOT / "examples/check_proof_input.json")
    selected.write_text(json.dumps(original), encoding="utf-8")
    (tmp_path / ".env").write_text("DO_NOT_READ_ME=secret", encoding="utf-8")
    try:
        assert client.main(["--input", str(selected), "--endpoint", f"http://127.0.0.1:{server.server_port}/proof"]) == 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    assert submitted == [original]
    assert set(submitted[0]) == client.FIELDS
    output = capsys.readouterr()
    assert json.loads(output.out) == result()
    assert "NEVER_PRINT" not in output.out
    assert "Advisory" in output.err
    assert not (tmp_path / ".showwork").exists()


@pytest.mark.parametrize("patch", [{"extra_secret": "no"}, {"claim": " "}, {"evidence": 5}])
def test_rejects_wrong_input_before_network(tmp_path, patch, monkeypatch):
    data = {**client.load_input(ROOT / "examples/check_proof_input.json"), **patch}
    file = tmp_path / "input.json"
    file.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(client, "submit", lambda *_: pytest.fail("Network must not be called"))
    assert client.main(["--input", str(file)]) == 2


def test_bounds_actual_input_bytes(tmp_path):
    file = tmp_path / "large.json"
    file.write_bytes(b"x" * (client.MAX_BYTES + 1))
    with pytest.raises(ValueError, match="32 KiB"):
        client.load_input(file)


@pytest.mark.parametrize("endpoint", ["http://example.com/proof", "file:///tmp/input", "https://user:secret@example.com/proof"])
def test_rejects_unsafe_transport(endpoint):
    with pytest.raises(ValueError):
        client.submit({}, endpoint)


def test_network_error_is_redacted_and_not_retried(monkeypatch, tmp_path, capsys):
    calls = []
    class Opener:
        def open(self, request, timeout):
            calls.append(timeout)
            raise HTTPError(request.full_url, 503, "PRIVATE_BODY", {}, io.BytesIO(b"PRIVATE_BODY"))
    monkeypatch.setattr(client, "build_opener", lambda *_: Opener())
    with pytest.raises(ValueError, match="HTTP 503") as error:
        client._submit_once(client.load_input(ROOT / "examples/check_proof_input.json"), client.DEFAULT_ENDPOINT)
    assert calls == [10]
    assert "PRIVATE_BODY" not in str(error.value)


def test_redirects_are_not_followed():
    assert client.NoRedirect().redirect_request(None, None, 307, "redirect", {}, "https://other.example") is None


@pytest.mark.parametrize("mode", ["trickle", "bad_chunk"])
def test_failed_http_exchange_is_bounded_and_redacted(mode, monkeypatch, capsys):
    # REGRESSION: trickling bodies reset socket timeouts; invalid chunks escaped
    # as IncompleteRead tracebacks instead of the documented redacted exit 2.
    received = threading.Event()
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            received.set()
            self.send_response(200)
            self.send_header("Transfer-Encoding" if mode == "bad_chunk" else "Content-Length",
                             "chunked" if mode == "bad_chunk" else "65536")
            self.end_headers()
            try:
                if mode == "bad_chunk":
                    self.wfile.write(b"PRIVATE_INVALID_CHUNK\r\n")
                    self.wfile.flush()
                else:
                    for _ in range(100):
                        self.wfile.write(b"x")
                        self.wfile.flush()
                        time.sleep(0.05)
            except OSError:
                pass
            self.close_connection = True
        def log_message(self, *_args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(client, "TIMEOUT_SECONDS", 1)
    started = time.monotonic()
    try:
        assert client.main(["--input", str(ROOT / "examples/check_proof_input.json"),
                            "--endpoint", f"http://127.0.0.1:{server.server_port}/proof"]) == 2
        assert time.monotonic() - started < 3
        assert received.is_set()
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    output = capsys.readouterr()
    assert not output.out
    assert "Endpoint" in output.err
    assert "PRIVATE" not in output.err
    assert "Traceback" not in output.err


def test_nested_provider_extras_are_not_echoed():
    value = result()
    value["usage"]["input_echo"] = "PRIVATE_CANARY"
    assert "PRIVATE_CANARY" not in json.dumps(client.validate_result(value))


@pytest.mark.parametrize("patch", [{"advisory": False}, {"verdict": "VERIFIED"}, {"confidence": float("nan")}, {"model": "jev-latest"}, {"requires_review": True}])
def test_invalid_results_are_not_accepted(patch):
    with pytest.raises(ValueError):
        client.validate_result({**result(), **patch})
