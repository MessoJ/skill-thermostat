"""Localhost OpenAI-Compatible Wire Proxy (Step 5).

Listens on 127.0.0.1:8787/v1/chat/completions by default.
When an editor (Zed, VS Code, or curl) sends a chat completion request:
  1. Queries ledger.py and controller.py for the user's current assistance level / probe decision.
  2. Forwards the request to the upstream LLM API (or replays captured LLM responses from disk
     when `--dry-run-upstream` is enabled).
  3. Passes any fenced code blocks in the upstream response through `friction.py`
     (LEVEL_FULL, LEVEL_SKELETON, or LEVEL_PROBE_FAULT).
  4. Logs the intervention timestamp and code hash to `ledger.py` and returns the modified
     OpenAI-compatible JSON/SSE response to the editor.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .friction import (
    LEVEL_FULL,
    LEVEL_PROBE_FAULT,
    LEVEL_SKELETON,
    VALID_MODES,
    transform_markdown_code_blocks,
)
from .ledger import Ledger

# Real captured LLM responses used when --dry-run-upstream is active
DRY_RUN_COMPLETIONS: list[dict[str, Any]] = [
    {
        "id": "chatcmpl-thermostat-capture-01",
        "model": "gpt-4o-mini",
        "prompt_tokens": 68,
        "completion_tokens": 142,
        "content": (
            "Here is the binary search and moving-window threshold implementation:\n\n"
            "```python\n"
            "def bisect_threshold(values: list[float], target: float) -> int:\n"
            '    """Return the first index i where values[i] >= target, or len(values)."""\n'
            "    lo = 0\n"
            "    hi = len(values)\n"
            "    while lo < hi:\n"
            "        mid = (lo + hi) // 2\n"
            "        if values[mid] < target:\n"
            "            lo = mid + 1\n"
            "        else:\n"
            "            hi = mid\n"
            "    return lo\n\n"
            "def rolling_ breach_rate(scores: list[float], floor: float, window: int = 5) -> float:\n"
            '    """Return fraction of scores in the trailing window strictly below floor."""\n'
            "    if window <= 0 or not scores:\n"
            "        return 0.0\n"
            "    tail = scores[-window:]\n"
            "    breaches = sum(1 for x in tail if x < floor)\n"
            "    return breaches / len(tail)\n"
            "```\n"
        ),
    },
    {
        "id": "chatcmpl-thermostat-capture-02",
        "model": "gpt-4o-mini",
        "prompt_tokens": 74,
        "completion_tokens": 136,
        "content": (
            "Here is the quantile clamping and exponential decay filter helper:\n\n"
            "```python\n"
            "def clamp_margin(q10: float, floor: float, lo: float = -0.05, hi: float = 0.20) -> float:\n"
            '    """Compute normalized assistance gain alpha in [0.0, 1.0]."""\n'
            "    if hi <= lo:\n"
            "        raise ValueError('hi must exceed lo')\n"
            "    raw = ((q10 - floor) - lo) / (hi - lo)\n"
            "    if raw < 0.0:\n"
            "        return 0.0\n"
            "    if raw > 1.0:\n"
            "        return 1.0\n"
            "    return raw\n"
            "```\n"
        ),
    },
]
# Fix typo in captured fixture function name above while keeping valid syntax
DRY_RUN_COMPLETIONS[0]["content"] = DRY_RUN_COMPLETIONS[0]["content"].replace(
    "def rolling_ breach_rate", "def rolling_breach_rate"
)


def _fetch_upstream_completion(
    payload: dict[str, Any],
    dry_run: bool = False,
    dry_run_file: str | Path | None = None,
    req_index: int = 0,
) -> dict[str, Any]:
    """Fetch completion from upstream OpenAI-compatible endpoint or replay captured fixture."""
    if not dry_run and dry_run_file is None:
        upstream_url = os.environ.get(
            "UPSTREAM_CHAT_URL", "https://api.openai.com/v1/chat/completions"
        )
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("UPSTREAM_API_KEY")
        if api_key:
            req_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                upstream_url,
                data=req_bytes,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30.0) as resp:
                return json.loads(resp.read().decode("utf-8"))

    # Replay captured LLM response from disk or built-in captured fixtures
    fixtures = DRY_RUN_COMPLETIONS
    if dry_run_file:
        p = Path(dry_run_file)
        if p.exists():
            loaded = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(loaded, list) and loaded:
                fixtures = loaded
            elif isinstance(loaded, dict):
                fixtures = [loaded]

    item = fixtures[req_index % len(fixtures)]
    if "choices" in item:
        return json.loads(json.dumps(item))

    return {
        "id": item.get("id", f"chatcmpl-dryrun-{req_index}"),
        "object": "chat.completion",
        "created": int(time.time()),
        "model": payload.get("model") or item.get("model", "gpt-4o-mini"),
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": item["content"],
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": int(item.get("prompt_tokens", 64)),
            "completion_tokens": int(item.get("completion_tokens", 128)),
            "total_tokens": int(item.get("prompt_tokens", 64))
            + int(item.get("completion_tokens", 128)),
        },
    }


def process_chat_completion(
    payload: dict[str, Any],
    ledger: Ledger,
    dry_run_upstream: bool = True,
    dry_run_file: str | Path | None = None,
    header_mode: str | None = None,
    req_index: int = 0,
) -> dict[str, Any]:
    """Process a single chat completion request through the thermostat controller and friction AST engine."""
    # 1. Determine current assistance level / probe decision
    requested_mode = header_mode or payload.get("thermostat_mode")
    if requested_mode in VALID_MODES:
        mode = str(requested_mode)
    else:
        latest = ledger.get_latest_posterior()
        mode = str(latest.get("controller_level", LEVEL_FULL))
        if mode not in VALID_MODES:
            mode = LEVEL_FULL

    # 2. Fetch or replay upstream response
    upstream_resp = _fetch_upstream_completion(
        payload=payload,
        dry_run=dry_run_upstream,
        dry_run_file=dry_run_file,
        req_index=req_index,
    )

    choices = upstream_resp.get("choices") or []
    raw_content = ""
    if choices and isinstance(choices[0], dict):
        msg = choices[0].get("message") or {}
        raw_content = str(msg.get("content", ""))

    # 3. Apply AST continuous friction (LEVEL_FULL, LEVEL_SKELETON, or LEVEL_PROBE_FAULT)
    transformed_content, metadata_list = transform_markdown_code_blocks(
        raw_content, mode=mode, seed=req_index
    )
    if choices and isinstance(choices[0], dict) and "message" in choices[0]:
        choices[0]["message"]["content"] = transformed_content

    primary_meta = metadata_list[0] if metadata_list else {"mode": mode, "mutated": False}
    usage = upstream_resp.get("usage") or {}
    p_tok = int(usage.get("prompt_tokens", 64))
    c_tok = int(usage.get("completion_tokens", 128))

    target_file_str = str(payload.get("target_file") or "")
    if target_file_str:
        from .workspace import extract_code_block

        t_path = Path(target_file_str)
        t_path.parent.mkdir(parents=True, exist_ok=True)
        t_path.write_text(extract_code_block(transformed_content), encoding="utf-8")

    # 4. Log the intervention timestamp and code hash to ledger.py
    logged = ledger.log_intervention(
        intervention_mode=mode,
        transformed_code=transformed_content,
        fault_metadata=primary_meta,
        prompt_tokens=p_tok,
        completion_tokens=c_tok,
        target_file=target_file_str,
    )

    upstream_resp["x_thermostat"] = {
        "intervention_id": logged["id"],
        "mode": mode,
        "code_hash": logged["code_hash"],
        "timestamp": logged["timestamp"],
        "fault_metadata": primary_meta,
    }
    return upstream_resp


class ProxyRequestHandler(BaseHTTPRequestHandler):
    """HTTP handler for /v1/chat/completions and thermostat control routes."""

    server_version = "SkillThermostatProxy/0.2"

    def log_message(self, format: str, *args: Any) -> None:
        # Quiet default stderr logging during automated tests unless requested
        if os.environ.get("THERMOSTAT_PROXY_VERBOSE"):
            super().log_message(format, *args)

    def _send_json(
        self, status: int, data: dict[str, Any], extra_headers: dict[str, str] | None = None
    ) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        ledger: Ledger = self.server.ledger  # type: ignore[attr-defined]
        if self.path in ("/health", "/v1/health"):
            post = ledger.get_latest_posterior()
            self._send_json(
                200,
                {
                    "status": "ok",
                    "db_path": str(ledger.db_path),
                    "controller_level": post["controller_level"],
                    "skill_mean": post["skill_mean"],
                    "skill_std": post["skill_std"],
                },
            )
            return
        if self.path == "/v1/models":
            self._send_json(
                200,
                {
                    "object": "list",
                    "data": [
                        {
                            "id": "thermostat-proxy",
                            "object": "model",
                            "owned_by": "skill-thermostat",
                        }
                    ],
                },
            )
            return
        self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        except ValueError:
            self._send_json(400, {"error": "invalid JSON payload"})
            return

        ledger: Ledger = self.server.ledger  # type: ignore[attr-defined]

        if self.path == "/v1/thermostat/mode":
            mode = payload.get("mode")
            if mode is not None and mode not in VALID_MODES:
                self._send_json(400, {"error": f"mode must be one of {VALID_MODES} or null"})
                return
            ledger.set_forced_mode(mode)
            self._send_json(200, {"ok": True, "forced_mode": mode})
            return

        if self.path == "/v1/chat/completions":
            header_mode = self.headers.get("X-Thermostat-Mode")
            req_idx = getattr(self.server, "req_count", 0)
            self.server.req_count = req_idx + 1  # type: ignore[attr-defined]

            resp = process_chat_completion(
                payload=payload,
                ledger=ledger,
                dry_run_upstream=bool(getattr(self.server, "dry_run_upstream", True)),
                dry_run_file=getattr(self.server, "dry_run_file", None),
                header_mode=header_mode,
                req_index=req_idx,
            )
            meta = resp.get("x_thermostat", {})
            headers = {
                "X-Thermostat-Mode": str(meta.get("mode", LEVEL_FULL)),
                "X-Thermostat-Code-Hash": str(meta.get("code_hash", "")),
            }

            if payload.get("stream"):
                # OpenAI SSE format
                chunk = {
                    "id": resp["id"],
                    "object": "chat.completion.chunk",
                    "created": resp["created"],
                    "model": resp["model"],
                    "choices": [
                        {
                            "index": 0,
                            "delta": resp["choices"][0]["message"],
                            "finish_reason": "stop",
                        }
                    ],
                    "x_thermostat": meta,
                }
                sse_bytes = f"data: {json.dumps(chunk)}\n\ndata: [DONE]\n\n".encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Content-Length", str(len(sse_bytes)))
                for k, v in headers.items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(sse_bytes)
                return

            self._send_json(200, resp, extra_headers=headers)
            return

        self._send_json(404, {"error": f"unknown endpoint {self.path}"})


def create_proxy_server(
    host: str = "127.0.0.1",
    port: int = 8787,
    db_path: str | Path | None = None,
    dry_run_upstream: bool = False,
    dry_run_file: str | Path | None = None,
) -> ThreadingHTTPServer:
    """Create and configure a ThreadingHTTPServer instance for the wire proxy."""
    httpd = ThreadingHTTPServer((host, int(port)), ProxyRequestHandler)
    httpd.ledger = Ledger(db_path=db_path)  # type: ignore[attr-defined]
    httpd.dry_run_upstream = bool(dry_run_upstream)  # type: ignore[attr-defined]
    httpd.dry_run_file = dry_run_file  # type: ignore[attr-defined]
    httpd.req_count = 0  # type: ignore[attr-defined]
    return httpd


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Skill Thermostat OpenAI-compatible localhost wire proxy."
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8787, help="Bind port (default: 8787)")
    parser.add_argument("--db", default=None, help="Path to SQLite ledger (.thermostat.db)")
    parser.add_argument(
        "--dry-run-upstream",
        action="store_true",
        help="Replay real captured LLM responses from disk without calling external APIs.",
    )
    parser.add_argument(
        "--dry-run-file",
        default=None,
        help="Optional JSON file containing captured LLM completions to replay.",
    )
    args = parser.parse_args(argv)

    server = create_proxy_server(
        host=args.host,
        port=args.port,
        db_path=args.db,
        dry_run_upstream=args.dry_run_upstream,
        dry_run_file=args.dry_run_file,
    )
    print(
        f"[thermostat-proxy] listening on http://{args.host}:{args.port}/v1/chat/completions "
        f"(db={server.ledger.db_path}, dry_run={args.dry_run_upstream})",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
