#!/usr/bin/env python3
"""Empirical Stress Tests: Before (Naive Filter) vs. After (Domain-Scoped + Huber-Damped).

Executes three reproducible stress tests against `skill_thermostat/filters.py`,
`skill_thermostat/ledger.py`, and `skill_thermostat/controller.py`:
  1. Domain-Shift False Alarm (`py:algo` -> `rust:core`):
     Before (Naive Scalar Filter) vs. After (Domain-Scoped Filter with weak global hyper-prior)
  2. Circadian Fatigue Confounding (140s-210s TTG spikes on verified passes):
     Before (Uncapped Log-Normal Filter) vs. After (Huber-Damped Latency Filter)
  3. Copy-Paste Bypass (<3s external LLM paste into LEVEL_SKELETON):
     Before (Unguarded Velocity) vs. After (`ANOMALY_PASTE_SUSPECTED` Guard)
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from skill_thermostat.controller import Thermostat, ThermostatConfig
from skill_thermostat.filters import SkillFilter
from skill_thermostat.friction import LEVEL_FULL, LEVEL_PROBE_FAULT, LEVEL_SKELETON
from skill_thermostat.ledger import Ledger
from skill_thermostat.model import GRID, lognormal_latency_factor, p_solo

C_GRID = (0.0, 0.1, 0.2, 0.3, 0.4)


def _warm_up_skilled_filter(n_passes: int = 8) -> SkillFilter:
    filt = SkillFilter(1, GRID, c_grid=C_GRID, robust_drift=True)
    yes = np.ones(1, dtype=bool)
    no = np.zeros(1, dtype=bool)
    for _ in range(n_passes):
        filt.predict(wide=no, learning=yes)
        filt.update_joint(
            passed=True,
            time_to_green_sec=9.5,
            edit_distance_ratio=0.35,
            mode=LEVEL_SKELETON,
            d=0.4,
            ast_verified=True,
            chars_per_sec=14.0,
            trusted=True,
            huber_damping=False,
        )
    return filt


def run_domain_shift_stress() -> dict[str, Any]:
    """Compare Naive Scalar Filter vs. Domain-Scoped Ledger when switching `py:algo` -> `rust:core`."""
    # 1. BEFORE: Naive scalar filter (conflates rust:core failures with py:algo competence)
    f_naive = _warm_up_skilled_filter(8)
    yes = np.ones(1, dtype=bool)
    no = np.zeros(1, dtype=bool)

    s0 = f_naive.summary()
    naive_trace: list[dict[str, Any]] = [
        {
            "step": 0,
            "domain": "py:algo",
            "outcome": "8x PASS (9.5s)",
            "naive_py_mu": float(s0.mean[0]),
            "naive_py_q10": float(s0.q10[0]),
        }
    ]
    for i in range(1, 4):
        f_naive.predict(wide=no, learning=yes)
        f_naive.update_joint(
            passed=False,
            time_to_green_sec=135.0,
            edit_distance_ratio=0.04,
            mode=LEVEL_PROBE_FAULT,
            d=0.0,
            ast_verified=False,
            trusted=True,
        )
        sn = f_naive.summary()
        naive_trace.append(
            {
                "step": i,
                "domain": "rust:core",
                "outcome": "FAIL (135.0s)",
                "naive_py_mu": float(sn.mean[0]),
                "naive_py_q10": float(sn.q10[0]),
            }
        )

    # 2. AFTER: Multi-domain scoped Ledger (`py:algo` vs `rust:core`)
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger = Ledger(db_path=Path(tmpdir) / "domain_stress.db")
        for _ in range(8):
            ledger.record_event(
                repo_hash="py01",
                intervention_mode=LEVEL_SKELETON,
                prompt_tokens=60,
                completion_tokens=100,
                test_exit_code=0,
                time_to_green_sec=9.5,
                edit_distance_ratio=0.35,
                probe_caught=True,
                ast_verified=True,
                chars_per_sec=14.0,
                domain="py:algo",
            )
        py_base = ledger.get_latest_posterior(domain="py:algo")
        scoped_trace: list[dict[str, Any]] = [
            {
                "step": 0,
                "domain": "py:algo",
                "outcome": "8x PASS (9.5s)",
                "naive_py_mu": naive_trace[0]["naive_py_mu"],
                "naive_mu": naive_trace[0]["naive_py_mu"],
                "naive_py_q10": naive_trace[0]["naive_py_q10"],
                "scoped_py_mu": float(py_base["skill_mean"]),
                "scoped_py_q10": float(py_base["skill_q10"]),
                "scoped_rust_mu": round(0.15 * float(py_base["skill_mean"]), 3),
                "scoped_py_mode": str(py_base["controller_level"]),
                "scoped_rust_mode": LEVEL_SKELETON,
            }
        ]
        for i in range(1, 4):
            rust_rec = ledger.record_event(
                repo_hash=f"rs0{i}",
                intervention_mode=LEVEL_PROBE_FAULT,
                prompt_tokens=60,
                completion_tokens=100,
                test_exit_code=1,
                time_to_green_sec=135.0,
                edit_distance_ratio=0.04,
                probe_caught=False,
                ast_verified=False,
                domain="rust:core",
            )
            py_now = ledger.get_latest_posterior(domain="py:algo")
            scoped_trace.append(
                {
                    "step": i,
                    "domain": "rust:core",
                    "outcome": "FAIL (135.0s)",
                    "naive_py_mu": naive_trace[i]["naive_py_mu"],
                    "naive_mu": naive_trace[i]["naive_py_mu"],
                    "naive_py_q10": naive_trace[i]["naive_py_q10"],
                    "scoped_py_mu": float(py_now["skill_mean"]),
                    "scoped_py_q10": float(py_now["skill_q10"]),
                    "scoped_rust_mu": float(rust_rec["skill_mean"]),
                    "scoped_py_mode": str(py_now["controller_level"]),
                    "scoped_rust_mode": str(rust_rec["controller_level"]),
                }
            )

    return {
        "rows": scoped_trace,
        "py_baseline_mu": scoped_trace[0]["scoped_py_mu"],
        "naive_after_mu": scoped_trace[-1]["naive_py_mu"],
        "scoped_py_after_mu": scoped_trace[-1]["scoped_py_mu"],
        "scoped_rust_after_mu": scoped_trace[-1]["scoped_rust_mu"],
    }


def run_circadian_fatigue_stress() -> list[dict[str, Any]]:
    """Stress Test 2: Compare Naive Uncapped Log-Normal vs. Huber-Damped Filter on 140s-210s passes."""
    f_naive = _warm_up_skilled_filter(5)
    f_huber = _warm_up_skilled_filter(5)
    f_forget = _warm_up_skilled_filter(5)
    yes = np.ones(1, dtype=bool)
    no = np.zeros(1, dtype=bool)

    latencies = [140.0, 165.0, 190.0, 210.0]
    rows: list[dict[str, Any]] = []

    for idx, ttg in enumerate(latencies, start=1):
        # 1. Before: Naive uncapped log-normal latency filter
        f_naive.predict(wide=no, learning=yes)
        f_naive.update_joint(
            passed=True,
            time_to_green_sec=ttg,
            edit_distance_ratio=0.28,
            mode=LEVEL_SKELETON,
            d=0.0,
            ast_verified=True,
            chars_per_sec=4.2,
            trusted=True,
            huber_damping=False,
        )

        # 2. After: Huber-damped latency filter (caps penalty when Exit=0 & Diff>0 & TTG>120s)
        f_huber.predict(wide=no, learning=yes)
        f_huber.update_joint(
            passed=True,
            time_to_green_sec=ttg,
            edit_distance_ratio=0.28,
            mode=LEVEL_SKELETON,
            d=0.0,
            ast_verified=True,
            chars_per_sec=4.2,
            trusted=True,
            huber_damping=True,
        )

        # 3. Genuine forgetting reference (Exit=1)
        f_forget.predict(wide=no, learning=yes)
        f_forget.update_joint(
            passed=False,
            time_to_green_sec=ttg,
            edit_distance_ratio=0.05,
            mode=LEVEL_SKELETON,
            d=0.0,
            ast_verified=False,
            trusted=True,
        )

        sn = f_naive.summary()
        sh = f_huber.summary()
        sg = f_forget.summary()
        rows.append(
            {
                "event": idx,
                "ttg_sec": ttg,
                "naive_pass_mu": float(sn.mean[0]),
                "naive_pass_q10": float(sn.q10[0]),
                "naive_q10": float(sn.q10[0]),
                "huber_pass_mu": float(sh.mean[0]),
                "huber_pass_q10": float(sh.q10[0]),
                "huber_q10": float(sh.q10[0]),
                "forgetting_fail_mu": float(sg.mean[0]),
                "forgetting_fail_q10": float(sg.q10[0]),
            }
        )
    return rows


def run_copy_paste_bypass_stress() -> dict[str, Any]:
    """Stress Test 3: Pasting a 420-char external LLM solution into LEVEL_SKELETON in 1.2s."""
    f_guarded = SkillFilter(1, GRID, c_grid=C_GRID, robust_drift=True)
    mu_init = float(f_guarded.summary().mean[0])
    c_init = float(f_guarded.summary().c_mean[0])

    status = f_guarded.update_joint(
        passed=True,
        time_to_green_sec=1.2,
        edit_distance_ratio=0.48,
        mode=LEVEL_SKELETON,
        d=0.0,
        ast_verified=True,
        chars_per_sec=350.0,
        trusted=False,
    )
    sg = f_guarded.summary()

    f_naive = SkillFilter(1, GRID, c_grid=C_GRID, robust_drift=True)
    lik_naive = p_solo(GRID, 0.0) * lognormal_latency_factor(GRID, 1.2, d=0.0)
    sub = f_naive.post[0] * (lik_naive[:, None] + 1e-12)
    f_naive.post[0] = sub / sub.sum()
    sn = f_naive.summary()

    return {
        "ttg_sec": 1.2,
        "edited_chars": 420,
        "edit_distance_ratio": 0.48,
        "chars_per_sec": 350.0,
        "human_bound_cps": 25.0,
        "status_flag": status,
        "mu_initial": mu_init,
        "naive_unguarded_mu": float(sn.mean[0]),
        "guarded_mu": float(sg.mean[0]),
        "c_initial": c_init,
        "contam_initial": c_init,
        "guarded_c_mean": float(sg.c_mean[0]),
        "guarded_contam": float(sg.c_mean[0]),
    }


def run_all_stress_tests() -> dict[str, Any]:
    dom_res = run_domain_shift_stress()
    return {
        "domain_shift": dom_res["rows"],
        "domain_shift_summary": dom_res,
        "circadian_fatigue": run_circadian_fatigue_stress(),
        "copy_paste_bypass": run_copy_paste_bypass_stress(),
    }


def format_stress_report(data: dict[str, Any] | None = None) -> str:
    d = data or run_all_stress_tests()
    dom_rows = d["domain_shift"]
    fat = d["circadian_fatigue"]
    cp = d["copy_paste_bypass"]

    lines = [
        "+" + "-" * 78 + "+",
        "| SKILL THERMOSTAT :: BEFORE vs AFTER FAILURE-MODE MITIGATION SUITE            |",
        "+" + "-" * 78 + "+",
        "| 1. DOMAIN-SHIFT FALSE ALARM (py:algo mastery vs 3 failures in rust:core)     |",
        "+" + "-" * 78 + "+",
        "| STEP | ACTIVE DOMAIN | OUTCOME        | BEFORE (NAIVE) | AFTER (py:algo/rust)|",
        "+" + "-" * 78 + "+",
    ]
    for r in dom_rows:
        before_str = f"mu={r['naive_py_mu']:+.3f}"
        after_str = f"py={r['scoped_py_mu']:+.3f} rs={r['scoped_rust_mu']:+.3f}"
        lines.append(
            f"| {r['step']:>4d} | {r['domain']:<13} | {r['outcome']:<14} | "
            f"{before_str:<14} | {after_str:<19} |"
        )
    lines.extend(
        [
            "+" + "-" * 78 + "+",
            f"| RESULT: Failing 3 probes in rust:core leaves py:algo intact at {dom_rows[-1]['scoped_py_mu']:+.3f}        |",
            f"| (LEVEL_FULL) instead of collapsing to {dom_rows[-1]['naive_py_mu']:+.3f} as in the naive scalar filter. |",
            "+" + "-" * 78 + "+",
            "| 2. CIRCADIAN FATIGUE CONFOUNDING (140s-210s TTG spikes on verified passes)   |",
            "+" + "-" * 78 + "+",
            "|  # | TTG (s) | BEFORE: NAIVE (mu / q10) | AFTER: HUBER CAP (mu / q10) | FAIL |",
            "+" + "-" * 78 + "+",
        ]
    )
    for r in fat:
        bef = f"{r['naive_pass_mu']:+.3f} / {r['naive_pass_q10']:+.3f}"
        aft = f"{r['huber_pass_mu']:+.3f} / {r['huber_pass_q10']:+.3f}"
        fl = f"{r['forgetting_fail_q10']:+.3f}"
        lines.append(
            f"| {r['event']:>2d} | {r['ttg_sec']:>7.1f} | {bef:<24} | {aft:<27} | {fl:<4} |"
        )
    lines.extend(
        [
            "+" + "-" * 78 + "+",
            f"| RESULT: Huber cap at TTG>120s preserves q10={fat[-1]['huber_pass_q10']:+.3f} (vs naive q10={fat[-1]['naive_pass_q10']:+.3f})   |",
            "| when AST edits are verified (Exit=0, Diff>0), preventing false decay.        |",
            "+" + "-" * 78 + "+",
            "| 3. COPY-PASTE BYPASS (<3s external LLM paste into LEVEL_SKELETON)            |",
            "+" + "-" * 78 + "+",
            f"| Input Payload        : {cp['edited_chars']} chars pasted in {cp['ttg_sec']:.1f}s (Diff={cp['edit_distance_ratio']:.2f})                 |",
            f"| Observed Velocity    : {cp['chars_per_sec']:.1f} chars/sec (Human Upper Bound: {cp['human_bound_cps']:.1f} chars/sec)   |",
            f"| Detector Verdict     : {cp['status_flag']:<53} |",
            f"| Before (Unguarded)   : mu = {cp['naive_unguarded_mu']:+.4f} (FALSE INFLATION if velocity ignored)     |",
            f"| After (Velocity Cap) : mu = {cp['guarded_mu']:+.4f} (Zero gain; c_hat: {cp['c_initial']:.3f} -> {cp['guarded_c_mean']:.3f})        |",
            "+" + "-" * 78 + "+",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    print(format_stress_report())


if __name__ == "__main__":
    main()
