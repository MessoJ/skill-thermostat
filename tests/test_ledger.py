"""Unit tests for Step 2: Local-Only Telemetry Ledger (skill_thermostat/ledger.py)."""
from __future__ import annotations

import sqlite3

from skill_thermostat.friction import LEVEL_FULL, LEVEL_PROBE_FAULT, LEVEL_SKELETON
from skill_thermostat.ledger import Ledger


def test_ledger_creates_tables_and_records_five_real_events_across_restarts(tmp_path):
    db_file = tmp_path / ".thermostat.db"

    # Process 1: Insert first 3 real event payloads
    ledger1 = Ledger(db_path=db_file)
    r1 = ledger1.record_event(
        repo_hash="1da9f174",
        intervention_mode=LEVEL_FULL,
        prompt_tokens=92,
        completion_tokens=184,
        test_exit_code=0,
        time_to_green_sec=11.4,
        edit_distance_ratio=0.04,
        timestamp=1730000001.0,
    )
    r2 = ledger1.record_event(
        repo_hash="8b3c29e1",
        intervention_mode=LEVEL_SKELETON,
        prompt_tokens=110,
        completion_tokens=96,
        test_exit_code=0,
        time_to_green_sec=22.7,
        edit_distance_ratio=0.41,
        timestamp=1730000045.0,
    )
    r3 = ledger1.record_event(
        repo_hash="4e91a02c",
        intervention_mode=LEVEL_PROBE_FAULT,
        prompt_tokens=88,
        completion_tokens=150,
        test_exit_code=1,
        time_to_green_sec=64.2,
        edit_distance_ratio=0.01,
        timestamp=1730000120.0,
        probe_caught=False,
    )
    del ledger1

    # Process 2 (simulated process restart): open same SQLite file and insert 2 more events
    ledger2 = Ledger(db_path=db_file)
    post_after_restart = ledger2.get_latest_posterior()
    assert abs(post_after_restart["skill_mean"] - r3["skill_mean"]) < 1e-6
    assert abs(post_after_restart["skill_std"] - r3["skill_std"]) < 1e-6

    r4 = ledger2.record_event(
        repo_hash="7f04d81b",
        intervention_mode=LEVEL_PROBE_FAULT,
        prompt_tokens=104,
        completion_tokens=162,
        test_exit_code=0,
        time_to_green_sec=18.5,
        edit_distance_ratio=0.19,
        timestamp=1730000180.0,
        probe_caught=True,
    )
    r5 = ledger2.record_event(
        repo_hash="9c12e77a",
        intervention_mode=LEVEL_SKELETON,
        prompt_tokens=95,
        completion_tokens=82,
        test_exit_code=0,
        time_to_green_sec=14.1,
        edit_distance_ratio=0.52,
        timestamp=1730000240.0,
    )

    # Catching probe + fast skeleton completion should increase posterior skill mean over r3
    assert r4["skill_mean"] > r3["skill_mean"]
    assert r5["skill_mean"] > r4["skill_mean"]

    # Verify raw SQLite tables directly via standard library sqlite3
    with sqlite3.connect(str(db_file)) as con:
        ev_rows = con.execute(
            "SELECT timestamp, repo_hash, intervention_mode, prompt_tokens, "
            "completion_tokens, test_exit_code, time_to_green_sec, edit_distance_ratio "
            "FROM events ORDER BY id ASC"
        ).fetchall()
        post_rows = con.execute(
            "SELECT timestamp, skill_mean, skill_std, controller_level "
            "FROM posteriors ORDER BY id ASC"
        ).fetchall()

    assert len(ev_rows) == 5
    assert len(post_rows) == 5
    assert ev_rows[0][1] == "1da9f174"
    assert ev_rows[4][1] == "9c12e77a"
    assert all(row[3] in (LEVEL_FULL, LEVEL_SKELETON, LEVEL_PROBE_FAULT) for row in post_rows)
