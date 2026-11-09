"""Unit and integration tests for Steps 4, 5, and 6 (observer, proxy, and CLI odometer)."""
from __future__ import annotations

import json
import sys
import threading
import urllib.request

from skill_thermostat import cli, observer, proxy
from skill_thermostat.friction import LEVEL_FULL, LEVEL_PROBE_FAULT, LEVEL_SKELETON
from skill_thermostat.ledger import Ledger


def test_observer_executes_command_and_updates_ledger(tmp_path, capsys):
    db_path = tmp_path / ".thermostat.db"
    ledger = Ledger(db_path=db_path)

    # Log a skeleton intervention first
    target_py = tmp_path / "solution.py"
    target_py.write_text(
        "def add_one(x: int) -> int:\n    return x + 1\n", encoding="utf-8"
    )
    ledger.log_intervention(
        intervention_mode=LEVEL_SKELETON,
        transformed_code='def add_one(x: int) -> int:\n    raise NotImplementedError("complete unassisted")\n',
        target_file=str(target_py),
        prompt_tokens=40,
        completion_tokens=60,
    )

    exit_code, record, summary_line = observer.run_observed_command(
        cmd=[sys.executable, "-c", "assert 1 + 1 == 2"],
        db_path=db_path,
        target_file=target_py,
        simulated_elapsed_sec=8.5,
    )
    captured = capsys.readouterr().out
    assert exit_code == 0
    assert "[thermostat] exit=0" in summary_line
    assert "skill_posterior=" in captured
    assert record["edit_distance_ratio"] > 0.0
    assert record["probe_caught"] is True
    assert ledger.get_active_intervention() is None


def test_proxy_three_modes_full_skeleton_and_probe_fault(tmp_path):
    db_path = tmp_path / ".thermostat.db"
    server = proxy.create_proxy_server(
        host="127.0.0.1",
        port=0,
        db_path=db_path,
        dry_run_upstream=True,
    )
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        url = f"http://127.0.0.1:{port}/v1/chat/completions"
        mode_url = f"http://127.0.0.1:{port}/v1/thermostat/mode"

        def _set_mode(m: str):
            req = urllib.request.Request(
                mode_url,
                data=json.dumps({"mode": m}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5.0) as r:
                assert r.status == 200

        def _chat():
            body = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "Write bisect_threshold"}],
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5.0) as r:
                return json.loads(r.read().decode("utf-8")), dict(r.headers)

        # Request 1: LEVEL_FULL -> returns full code untouched
        _set_mode(LEVEL_FULL)
        resp1, hdr1 = _chat()
        code1 = resp1["choices"][0]["message"]["content"]
        assert resp1["x_thermostat"]["mode"] == LEVEL_FULL
        assert "while lo < hi:" in code1
        assert "NotImplementedError" not in code1

        # Request 2: LEVEL_SKELETON -> returns AST-stripped function signatures
        _set_mode(LEVEL_SKELETON)
        resp2, hdr2 = _chat()
        code2 = resp2["choices"][0]["message"]["content"]
        assert resp2["x_thermostat"]["mode"] == LEVEL_SKELETON
        assert "NotImplementedError('complete unassisted')" in code2 or 'NotImplementedError("complete unassisted")' in code2

        # Request 3: LEVEL_PROBE_FAULT -> injects boundary mutation and logs active probe in .thermostat.db
        _set_mode(LEVEL_PROBE_FAULT)
        resp3, hdr3 = _chat()
        code3 = resp3["choices"][0]["message"]["content"]
        assert resp3["x_thermostat"]["mode"] == LEVEL_PROBE_FAULT
        assert resp3["x_thermostat"]["fault_metadata"]["mutated"] is True
        assert code3 != code1

        ledger = Ledger(db_path=db_path)
        active = ledger.get_active_intervention()
        assert active is not None
        assert active["intervention_mode"] == LEVEL_PROBE_FAULT
        assert active["fault_metadata"]["mutated"] is True
    finally:
        server.shutdown()
        server.server_close()


def test_cli_status_and_export_proof(tmp_path, capsys):
    db_path = tmp_path / ".thermostat.db"
    ledger = Ledger(db_path=db_path)
    for i in range(5):
        mode = [LEVEL_FULL, LEVEL_SKELETON, LEVEL_PROBE_FAULT, LEVEL_SKELETON, LEVEL_PROBE_FAULT][i]
        ledger.record_event(
            repo_hash=f"deadbeef0{i}",
            intervention_mode=mode,
            prompt_tokens=80,
            completion_tokens=120,
            test_exit_code=0,
            time_to_green_sec=12.0 + i * 3.5,
            edit_distance_ratio=0.25 + i * 0.05,
            probe_caught=True if mode == LEVEL_PROBE_FAULT else None,
        )

    rc_status = cli.main(["status", "--db", str(db_path)])
    out_status = capsys.readouterr().out
    assert rc_status == 0
    assert "SKILL THERMOSTAT :: LOCAL TELEMETRY ODOMETER" in out_status
    assert "Probe Catch Rate" in out_status
    assert "POSTERIOR SKILL TRAJECTORY" in out_status
    for line in out_status.strip().splitlines():
        assert len(line) <= 80

    proof_file = tmp_path / "proof.json"
    rc_proof = cli.main(["export-proof", "--db", str(db_path), "--out", str(proof_file)])
    out_proof = capsys.readouterr().out
    assert rc_proof == 0
    receipt = json.loads(out_proof)
    assert receipt["schema_version"] == "skill-thermostat-proof/v1"
    assert len(receipt["hash_chain"]["event_hashes"]) == 5
    assert "signature" in receipt and receipt["signature"]["algorithm"] == "HMAC-SHA256"
    assert proof_file.exists()
