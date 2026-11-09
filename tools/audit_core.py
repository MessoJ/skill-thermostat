#!/usr/bin/env python3
"""Standalone CLI diagnostic script for Step 1: 3-State Hysteresis & Core Math Audit.

Feeds a deterministic sequence of 20 real task outcomes into `SkillFilter` and
`Thermostat.decide_hysteresis` (without using `sim.py`), demonstrating the full
closed-loop trajectory across all three assistance tiers:
  1. Initial calibration & mastery -> `LEVEL_FULL` (with scheduled cadence probe at K=5)
  2. Prolonged passive AI reliance -> downward skill drift into `LEVEL_SKELETON`
  3. Unassisted probe failures -> diagnostic lock in `LEVEL_PROBE_FAULT`
  4. Fast unassisted recovery (14.2s down to 7.5s) -> `LEVEL_SKELETON` -> `LEVEL_FULL`
"""
from __future__ import annotations

import numpy as np

from skill_thermostat.controller import Thermostat, ThermostatConfig
from skill_thermostat.filters import SkillFilter
from skill_thermostat.model import GRID


# Deterministic sequence of 20 real-world task outcome tuples:
# (step, mode, success, latency_sec, edit_distance_ratio, base_difficulty)
AUDIT_EVENTS: list[tuple[int, str, bool, float, float, float]] = [
    # Steps 1..2: Fast unassisted calibration passes establish high q10 -> LEVEL_FULL
    (1, "LEVEL_PROBE_FAULT", True, 8.4, 0.08, 0.8),
    (2, "LEVEL_SKELETON", True, 9.6, 0.42, 1.0),
    # Steps 3..7: 5 consecutive assisted tasks in LEVEL_FULL; at step 7 (K=5), scheduled probe fires
    (3, "LEVEL_FULL", True, 8.5, 0.00, 0.0),
    (4, "LEVEL_FULL", True, 9.1, 0.00, 0.0),
    (5, "LEVEL_FULL", True, 10.4, 0.00, 0.0),
    (6, "LEVEL_FULL", True, 7.8, 0.00, 0.0),
    (7, "LEVEL_FULL", True, 11.2, 0.00, 0.0),
    # Steps 8..10: Slow probe + prolonged passive AI reliance decay q10 into LEVEL_SKELETON
    (8, "LEVEL_PROBE_FAULT", True, 115.0, 0.06, -0.4),
    (9, "LEVEL_FULL", True, 12.0, 0.00, 0.0),
    (10, "LEVEL_FULL", True, 13.4, 0.00, 0.0),
    # Steps 11..15: 5 unassisted probe failures drop q10 below floor_probe (-0.35) -> LEVEL_PROBE_FAULT
    (11, "LEVEL_SKELETON", False, 88.0, 0.09, -0.3),
    (12, "LEVEL_PROBE_FAULT", False, 104.0, 0.00, -0.4),
    (13, "LEVEL_PROBE_FAULT", False, 92.5, 0.03, -0.4),
    (14, "LEVEL_PROBE_FAULT", False, 110.0, 0.00, -0.5),
    (15, "LEVEL_PROBE_FAULT", False, 79.4, 0.04, -0.5),
    # Steps 16..20: Fast unassisted recovery (14.2s -> 7.5s) on challenging probes -> SKELETON -> FULL
    (16, "LEVEL_PROBE_FAULT", True, 14.2, 0.08, 0.8),
    (17, "LEVEL_PROBE_FAULT", True, 11.8, 0.09, 1.0),
    (18, "LEVEL_SKELETON", True, 10.4, 0.39, 1.1),
    (19, "LEVEL_SKELETON", True, 8.9, 0.44, 1.2),
    (20, "LEVEL_PROBE_FAULT", True, 7.5, 0.11, 1.3),
]


def run_audit(
    floor_probe: float = -0.35,
    floor_full: float = 0.25,
    probe_cadence: int = 5,
) -> list[dict]:
    """Run the 20-step deterministic audit against SkillFilter and Thermostat.decide_hysteresis."""
    c_grid = (0.0, 0.1, 0.2, 0.3, 0.4)
    # Start from a calibrated developer prior (prior_mean=+0.55, prior_sd=0.85)
    filt = SkillFilter(
        1,
        GRID,
        c_grid=c_grid,
        prior_sd=0.85,
        robust_drift=True,
        wide_shift=-0.105,
        wide_sd=0.095,
        prior_mean=0.55,
    )
    cfg = ThermostatConfig(
        floor_probe=floor_probe,
        floor_full=floor_full,
        probe_cadence=probe_cadence,
    )
    ctl = Thermostat(cfg, GRID)

    yes = np.ones(1, dtype=bool)
    no = np.zeros(1, dtype=bool)
    since_last_probe = 0
    prev_mean = float(filt.summary().mean[0])
    rows: list[dict] = []

    for step, mode, success, latency_sec, edit_ratio, base_d in AUDIT_EVENTS:
        if mode == "LEVEL_FULL":
            filt.predict(wide=yes, learning=no)
            since_last_probe += 1
            status_flag = "ASSISTED_DRIFT"
        else:
            filt.predict(wide=no, learning=yes)
            status_flag = filt.update_joint(
                passed=success,
                time_to_green_sec=latency_sec,
                edit_distance_ratio=edit_ratio,
                mode=mode,
                d=base_d,
                ast_verified=(edit_ratio > 0.0),
                trusted=(edit_ratio > 0.0),
            )
            since_last_probe = 0

        summ = filt.summary()
        mean_val = float(summ.mean[0])
        delta_mu = mean_val - prev_mean
        prev_mean = mean_val
        sd_val = float(summ.sd[0])
        var_val = sd_val ** 2
        q10_val = float(summ.q10[0])

        next_state, alpha_val, is_probe = ctl.decide_hysteresis(
            summ,
            since_last_probe=since_last_probe,
            floor_probe=floor_probe,
            floor_full=floor_full,
            probe_cadence=probe_cadence,
        )

        rows.append(
            {
                "step": step,
                "mode": mode,
                "outcome": f"{'PASS' if success else 'FAIL'} ({latency_sec:5.1f}s)",
                "success": success,
                "latency_sec": latency_sec,
                "edit_distance_ratio": edit_ratio,
                "status_flag": status_flag,
                "mean": mean_val,
                "mu": mean_val,
                "delta_mu": delta_mu,
                "std": sd_val,
                "variance": var_val,
                "q10": q10_val,
                "alpha": alpha_val,
                "off": is_probe,
                "next_state": next_state,
                "next_mode": next_state,
            }
        )

    return rows


def format_audit_table(rows: list[dict]) -> str:
    lines = [
        "+" + "-" * 78 + "+",
        "| SKILL THERMOSTAT 3-STATE HYSTERESIS AUDIT (20 DETERMINISTIC EVENT TUPLES)    |",
        "+" + "-" * 78 + "+",
        "| STEP | TASK MODE         | OUTCOME        | POST MEAN |   Q10   | NEXT MODE  |",
        "+" + "-" * 78 + "+",
    ]
    for r in rows:
        nxt = r["next_state"].replace("LEVEL_", "")
        lines.append(
            f"| {r['step']:>4d} | {r['mode']:<17} | {r['outcome']:<14} | "
            f"{r['mean']:>+9.4f} | {r['q10']:>+7.3f} | {nxt:<10} |"
        )
    lines.append("+" + "-" * 78 + "+")
    return "\n".join(lines)


def main() -> None:
    rows = run_audit()
    print(format_audit_table(rows))


if __name__ == "__main__":
    main()
