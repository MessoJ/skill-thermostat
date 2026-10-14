"""Flask app for the arm-based study (engine: pilot/study.py).

    python -m pilot.study_app [--db study.db] [--port 8001]

ADMIN_TOKEN (env) protects /api/admin/*; without it those routes only answer from localhost.
ANTHROPIC_API_KEY (env) switches the helper from the offline stub to Claude.
"""
import argparse
import hmac
import os
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from .study import Engine, EngineError

STATIC = Path(__file__).parent / "static"


def create_app(db_path="study.db", helper=None):
    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = 200_000
    eng = Engine(db_path, helper)
    app.engine = eng

    @app.errorhandler(EngineError)
    def _engine_error(e):
        return jsonify(error=str(e)), e.status

    @app.errorhandler(413)
    def _too_big(_):
        return jsonify(error="request too large"), 413

    def body():
        return request.get_json(silent=True) or {}

    def need_user():
        uid = request.headers.get("X-User") or body().get("user")
        if not uid:
            raise EngineError("missing user")
        return uid

    @app.get("/")
    def index():
        return send_from_directory(STATIC, "index.html")

    @app.post("/api/join")
    def join():
        return jsonify(eng.join(bool(body().get("consent"))))

    @app.post("/api/next")
    def next_task():
        return jsonify(eng.next_task(need_user(), urgent=bool(body().get("urgent"))))

    @app.post("/api/event")
    def event():
        b = body()
        eng.log_event(need_user(), int(b.get("task_id", 0)), b.get("kind", ""), b.get("data"))
        return jsonify(ok=True)

    @app.post("/api/run")
    def run():
        b = body()
        return jsonify(eng.run_examples(need_user(), int(b.get("task_id", 0)), str(b.get("code", ""))))

    @app.post("/api/submit")
    def submit():
        b = body()
        return jsonify(eng.submit(need_user(), int(b.get("task_id", 0)), str(b.get("code", ""))))

    @app.post("/api/helper")
    def helper_route():
        b = body()
        return jsonify(eng.ask_helper(need_user(), int(b.get("task_id", 0)), str(b.get("message", ""))[:2000],
                                      str(b.get("code", ""))[:20000]))

    @app.get("/api/status")
    def status():
        return jsonify(eng.status(need_user()))

    @app.get("/api/admin/summary")
    def admin_summary():
        token = os.environ.get("ADMIN_TOKEN")
        if token:
            if not hmac.compare_digest(request.headers.get("X-Admin", ""), token):
                return jsonify(error="forbidden"), 403
        elif request.remote_addr not in ("127.0.0.1", "::1"):
            return jsonify(error="forbidden"), 403
        return jsonify(eng.summary())

    return app


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="study.db")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8001)
    a = ap.parse_args()
    create_app(a.db).run(host=a.host, port=a.port, threaded=True)
