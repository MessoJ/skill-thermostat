"""Tiny stdlib HTTP server for the pilot app.

    python -m pilot.server [--host 127.0.0.1] [--port 8000] [--db pilot.db] [--config sweep_out/sweep_pick.json]

Set PILOT_ADMIN_TOKEN to enable GET /api/export?token=... (the study organiser's data dump).
Set ANTHROPIC_API_KEY to use the live Claude helper instead of the offline stub.
"""
import argparse
import hmac
import json
import os
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .assistant import make_assistant
from .engine import Participant, load_config
from .store import Store

STATIC = Path(__file__).parent / "static" / "index.html"


class App:
    def __init__(self, store, cfg, assistant, admin_token=None):
        self.store, self.cfg, self.assistant, self.admin_token = store, cfg, assistant, admin_token
        self.people, self.locks, self.guard = {}, {}, threading.Lock()

    def _get(self, pid):
        with self.guard:
            if pid not in self.people:
                row = self.store.participant(pid)
                if row is None:
                    return None, None
                p = Participant(self.store, pid, row[2], self.cfg, self.assistant)
                p.replay()
                self.people[pid], self.locks[pid] = p, threading.Lock()
            return self.people[pid], self.locks[pid]

    def handle(self, method, path, query, body):
        """Return (status, json-able object)."""
        if method == "GET" and path == "/api/export":
            tok = (query.get("token") or [""])[0]
            if not self.admin_token or not hmac.compare_digest(tok, self.admin_token):
                return 403, {"error": "export disabled or bad token"}
            return 200, self.store.export()
        if method != "POST":
            return 404, {"error": "not found"}
        if path == "/api/start":
            name = str(body.get("name", "")).strip()[:40] or "anonymous"
            pid, seed = secrets.token_hex(8), secrets.randbits(31)
            self.store.add_participant(pid, name, seed)
            return 200, {"pid": pid}
        person, lock = self._get(str(body.get("pid", "")))
        if person is None:
            return 404, {"error": "unknown participant"}
        with lock:
            try:
                if path == "/api/next":
                    return 200, {**person.serve(), "state": person.state()}
                if path == "/api/state":
                    return 200, person.state()
                if path == "/api/submit":
                    code = str(body.get("code", ""))
                    secs = body.get("secs")
                    res = person.submit(code, max(0, int(body.get("paste_attempts", 0))),
                                        max(0, int(body.get("burst_inserts", 0))),
                                        float(secs) if isinstance(secs, (int, float)) else None)
                    return 200, {**res, "state": person.state()}
                if path == "/api/help":
                    return 200, person.help(str(body.get("code", "")), str(body.get("message", ""))[:500])
            except PermissionError as e:
                return 403, {"error": str(e)}
            except (ValueError, TypeError) as e:
                return 400, {"error": str(e)}
        return 404, {"error": "not found"}


def make_handler(app):
    class H(BaseHTTPRequestHandler):
        def _send(self, status, obj=None, raw=None, ctype="application/json"):
            data = raw if raw is not None else json.dumps(obj).encode()
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            u = urlparse(self.path)
            if u.path == "/":
                return self._send(200, raw=STATIC.read_bytes(), ctype="text/html; charset=utf-8")
            self._send(*app.handle("GET", u.path, parse_qs(u.query), {}))

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            if n > 100_000:
                return self._send(413, {"error": "too large"})
            try:
                body = json.loads(self.rfile.read(n) or b"{}")
                if not isinstance(body, dict):
                    raise ValueError
            except ValueError:
                return self._send(400, {"error": "bad json"})
            self._send(*app.handle("POST", urlparse(self.path).path, {}, body))

        def log_message(self, *a):
            pass

    return H


def serve(app, host="127.0.0.1", port=8000):
    return ThreadingHTTPServer((host, port), make_handler(app))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--db", default="pilot.db")
    ap.add_argument("--config", default="sweep_out/sweep_pick.json")
    a = ap.parse_args()
    app = App(Store(a.db), load_config(a.config), make_assistant(), os.environ.get("PILOT_ADMIN_TOKEN"))
    srv = serve(app, a.host, a.port)
    print(f"Pilot running at http://{a.host}:{a.port}  (helper: {type(app.assistant).__name__})")
    srv.serve_forever()
