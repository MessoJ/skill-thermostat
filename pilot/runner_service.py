"""Tiny HTTP service that runs submissions. Runs inside its own container (see docker-compose.yml).

    python -m pilot.runner_service [--host 0.0.0.0] [--port 9000]      RUNNER_KEY=... requires header X-Runner-Key

POST /run  {code, fname, cases, expected} -> the dict returned by pilot.runner.run_local.
It holds no data and no secrets. The container supplies the isolation: no internet, read-only filesystem, non-root user,
dropped capabilities, memory and process limits. Standard library only.
"""
import argparse
import hmac
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .runner import run_local

MAX_BODY = 200_000
SLOTS = threading.BoundedSemaphore(int(os.environ.get("RUNNER_SLOTS", "4")))


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._send(200, {"ok": True}) if self.path == "/health" else self._send(404, {"error": "not found"})

    def do_POST(self):
        key = os.environ.get("RUNNER_KEY")
        if key and not hmac.compare_digest(self.headers.get("X-Runner-Key", ""), key):
            return self._send(403, {"error": "forbidden"})
        if self.path != "/run":
            return self._send(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if not 0 < n <= MAX_BODY:
                return self._send(413, {"error": "bad size"})
            job = json.loads(self.rfile.read(n))
            code, fname, cases, expected = job["code"], job["fname"], job["cases"], job["expected"]
            if not (isinstance(code, str) and isinstance(fname, str) and fname.isidentifier()
                    and isinstance(cases, list) and isinstance(expected, list) and len(cases) == len(expected) <= 50
                    and all(isinstance(c, list) for c in cases)):
                return self._send(400, {"error": "bad job"})
        except (ValueError, KeyError, TypeError):
            return self._send(400, {"error": "bad job"})
        if not SLOTS.acquire(timeout=20):
            return self._send(503, {"error": "busy"})
        try:
            self._send(200, run_local(code, fname, cases, expected))
        finally:
            SLOTS.release()

    def log_message(self, *a):
        pass


def make_server(host="127.0.0.1", port=0):
    return ThreadingHTTPServer((host, port), Handler)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=9000)
    a = ap.parse_args()
    make_server(a.host, a.port).serve_forever()
