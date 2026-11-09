"""Unit tests for Milestone 2 & Milestone 3 physical workspace loop, 3-state hysteresis, domain scoping, and Mozilla LOI export."""
from __future__ import annotations

import sys

from skill_thermostat.friction import LEVEL_FULL, LEVEL_PROBE_FAULT, LEVEL_SKELETON
from skill_thermostat.ledger import Ledger
from skill_thermostat.observer import run_observed_command
from skill_thermostat.workspace import (
    REFERENCE_TARGET_SOURCE,
    inject_on_disk_intervention,
    restore_reference_target,
)
from tools.audit_core import run_audit
from tools.export_loi_metrics import export_loi_file
from tools.stress_failures import run_all_stress_tests


def test_physical_workspace_fail_unedited_then_repair_cycle(tmp_path):
    """Verify the physical loop on `rolling_breach_rate`:
    1. Inject LEVEL_PROBE_FAULT onto disk -> run pytest without editing -> Exit != 0, Diff == 0.000, mu drops, pytest_output contains failure.
    2. Repair the mutated boundary operator on disk -> re-run pytest -> Exit == 0, Diff > 0.000, mu rises.
    """
    db_path = tmp_path / ".thermostat.db"
    target_py = tmp_path / "target_algo.py"
    test_py = tmp_path / "test_target_algo.py"

    test_py.write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(tmp_path)!r})\n"
        "from target_algo import bisect_threshold, rolling_breach_rate, token_bucket_allow, ewma_variance\n\n"
        "def test_all():\n"
        "    assert bisect_threshold([1.0, 2.0, 2.0, 3.0], 2.0) == 1\n"
        "    assert rolling_breach_rate([-0.25, -0.25], -0.25, window=2) == 0.0\n"
        "    assert token_bucket_allow(5.0, 10.0, 1.0, 0.0, 5.0) == (True, 0.0)\n"
        "    assert abs(ewma_variance([0.0, 4.0], alpha=0.25) - 3.0) < 1e-9\n",
        encoding="utf-8",
    )

    ledger = Ledger(db_path=db_path)
    mu_initial = ledger.get_latest_posterior()["skill_mean"]

    # Inject LEVEL_PROBE_FAULT specifically targeting `rolling_breach_rate`
    injected = inject_on_disk_intervention(
        mode=LEVEL_PROBE_FAULT,
        ledger=ledger,
        target_path=target_py,
        seed=1,
        target_function="rolling_breach_rate",
        domain="py:algo",
    )
    assert injected["fault_metadata"]["mutated"] is True
    assert injected["fault_metadata"]["target_function"] == "rolling_breach_rate"
    assert target_py.read_text(encoding="utf-8") != REFERENCE_TARGET_SOURCE

    # Run 1: Without editing target_py, run observer + pytest -> MUST fail with Diff == 0.0
    exit1, rec1, _ = run_observed_command(
        cmd=[sys.executable, "-m", "pytest", str(test_py)],
        db_path=db_path,
        target_file=target_py,
        domain="py:algo",
    )
    assert exit1 != 0
    assert rec1["edit_distance_ratio"] == 0.0
    assert rec1["verification_status"] == "PROBE_FAILED_UNEDITED"
    assert rec1["skill_mean"] < mu_initial
    assert "FAILED" in rec1["pytest_output"] or "AssertionError" in rec1["pytest_output"]

    # Run 2: Repair target_py back to reference implementation and re-run observer + pytest
    restore_reference_target(target_py)
    exit2, rec2, _ = run_observed_command(
        cmd=[sys.executable, "-m", "pytest", str(test_py)],
        db_path=db_path,
        target_file=target_py,
        simulated_elapsed_sec=11.4,
        domain="py:algo",
    )
    assert exit2 == 0
    assert rec2["edit_distance_ratio"] > 0.0
    assert rec2["probe_caught"] is True
    assert rec2["verification_status"] == "VERIFIED_PROBE_CATCH"
    assert rec2["skill_mean"] > rec1["skill_mean"]
    assert "passed" in rec2["pytest_output"]


def test_audit_core_transitions_across_all_three_hysteresis_states():
    rows = run_audit()
    assert len(rows) == 20
    next_modes = {r["next_mode"] for r in rows}
    assert LEVEL_FULL in next_modes
    assert LEVEL_SKELETON in next_modes
    assert LEVEL_PROBE_FAULT in next_modes


def test_stress_failures_suite_outputs_expected_before_and_after_boundaries():
    res = run_all_stress_tests()
    dom = res["domain_shift"]
    assert dom[0]["naive_mu"] > 2.0
    # Naive filter collapses py:algo posterior after 3 rust:core failures:
    assert dom[-1]["naive_mu"] < dom[0]["naive_mu"] - 1.0
    # Domain-scoped filter keeps py:algo intact at its mastered level:
    assert abs(dom[-1]["scoped_py_mu"] - dom[0]["scoped_py_mu"]) < 1e-9
    assert dom[-1]["scoped_rust_mu"] < -0.5

    fat = res["circadian_fatigue"]
    assert fat[-1]["huber_q10"] > fat[-1]["naive_q10"] + 0.15

    cp = res["copy_paste_bypass"]
    assert cp["status_flag"] == "ANOMALY_PASTE_SUSPECTED"
    assert abs(cp["guarded_mu"] - cp["mu_initial"]) < 1e-12
    assert cp["naive_unguarded_mu"] > cp["guarded_mu"] + 0.3


def test_domain_scoping_in_sqlite_ledger(tmp_path):
    db_path = tmp_path / ".thermostat.db"
    ledger = Ledger(db_path=db_path)

    # Record a fast pass in py:algo
    r1 = ledger.record_event(
        repo_hash="abc1234",
        intervention_mode=LEVEL_PROBE_FAULT,
        prompt_tokens=50,
        completion_tokens=80,
        test_exit_code=0,
        time_to_green_sec=9.5,
        edit_distance_ratio=0.05,
        probe_caught=True,
        ast_verified=True,
        chars_per_sec=4.0,
        verification_status="VERIFIED_PROBE_CATCH",
        domain="py:algo",
    )
    py_mu_before = r1["skill_mean"]
    assert py_mu_before > 0.3

    # Record a failure in rust:core
    r2 = ledger.record_event(
        repo_hash="abc1234",
        intervention_mode=LEVEL_PROBE_FAULT,
        prompt_tokens=50,
        completion_tokens=80,
        test_exit_code=1,
        time_to_green_sec=90.0,
        edit_distance_ratio=0.0,
        probe_caught=False,
        ast_verified=False,
        chars_per_sec=0.0,
        verification_status="PROBE_FAILED_UNEDITED",
        domain="rust:core",
    )
    assert r2["domain"] == "rust:core"
    assert r2["skill_mean"] < 0.0

    # Verify py:algo posterior in ledger was not overwritten by rust:core failure
    py_post = ledger.get_latest_posterior(domain="py:algo")
    assert abs(py_post["skill_mean"] - py_mu_before) < 1e-9


def test_export_loi_metrics_generates_word_count_verified_markdown(tmp_path):
    out_md = tmp_path / "MOZILLA_LOI_DRAFT.md"
    sections, md = export_loi_file(out_path=out_md)
    assert out_md.exists()
    assert "MOZILLA FOUNDATION 2027-2028 TRACK II" in md
    for key in (
        "project_summary",
        "bayesian_calibration",
        "failure_mode_honesty",
        "privacy_and_open_source",
    ):
        assert sections[key]["word_count"] <= sections[key]["limit"]
        assert sections[key]["word_count"] >= 80
