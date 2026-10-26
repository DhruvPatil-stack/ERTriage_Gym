"""Ollama HTTP adapter for the ESI benchmark.

The adapter calls the local Ollama server with a POST request.
Retries happen on connection or server failures.
"""
import http.server
import json
import os
import socketserver
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from eval.eval_config import (  # noqa: E402
    OLLAMA_URL,
    CALL_TIMEOUT_S,
    CALL_RETRIES,
    OLLAMA_OPTIONS,
)
from eval.adapters import BaseAdapter  # noqa: E402


class OllamaAdapter(BaseAdapter):
    """Call the Ollama generate endpoint for one prompt."""

    def __init__(self, model_tag: str, options=None, url=None):
        self.name = model_tag
        self.model_tag = model_tag
        self.options = options if options is not None else dict(OLLAMA_OPTIONS)
        self.url = url if url is not None else OLLAMA_URL
        self.model_digest = None

    def ask(self, prompt: str) -> str:
        """Return the model text or an empty string after all retries fail."""
        body = json.dumps({
            "model": self.model_tag,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": self.options,
        }).encode("utf-8")
        last_err = None
        for attempt in range(CALL_RETRIES + 1):
            try:
                req = urllib.request.Request(
                    f"{self.url}/api/generate",
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=CALL_TIMEOUT_S) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data.get("response", "")
            except Exception as e:
                last_err = e
                if attempt == CALL_RETRIES:
                    return ""
                time.sleep(1)
        return ""


# ---- Mock server test helper. ----

def test_ollama_mock_server():
    """Start a mock HTTP server. Verify body shape and failure path."""
    received = {"body": None, "count": 0, "fail_mode": False}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            received["body"] = json.loads(raw.decode("utf-8"))
            received["count"] += 1
            if received["fail_mode"]:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"server error")
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"response": '{"esi_level": 3, "reason": "mock"}'}).encode())

        def log_message(self, *args, **kwargs):
            return

    port = 19999
    server = socketserver.TCPServer(("localhost", port), Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        adapter = OllamaAdapter("mock:latest", url=f"http://localhost:{port}")
        out = adapter.ask("hello")
        assert out == '{"esi_level": 3, "reason": "mock"}', out
        body = received["body"]
        assert body["model"] == "mock:latest"
        assert body["stream"] is False
        assert body["format"] == "json"
        assert "options" in body
        # Now switch to fail mode and expect empty string.
        received["fail_mode"] = True
        received["count"] = 0
        out2 = adapter.ask("hello")
        assert out2 == ""
        assert received["count"] >= 1
        print("test_ollama_mock_server passed")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    test_ollama_mock_server()
