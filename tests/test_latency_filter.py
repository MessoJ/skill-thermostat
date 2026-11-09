"""Unit tests for Milestone 2 Step 2: Latency- and Diff-Sensitive Bayesian Likelihoods."""
from __future__ import annotations

import numpy as np

from skill_thermostat.filters import SkillFilter
from skill_thermostat.friction import LEVEL_PROBE_FAULT, LEVEL_SKELETON
from skill_thermostat.model import GRID


def test_fast_vs_slow_time_to_green_produces_distinct_posterior_means():
    """Two passing runs with ttg=8.0s vs ttg=120.0s must produce mu_fast > mu_slow."""
    f_fast = SkillFilter(1, GRID, c_grid=(0.0, 0.1, 0.2, 0.3, 0.4), robust_drift=True)
    f_slow = SkillFilter(1, GRID, c_grid=(0.0, 0.1, 0.2, 0.3, 0.4), robust_drift=True)

    status_fast = f_fast.update_joint(
        passed=True,
        time_to_green_sec=8.0,
        edit_distance_ratio=0.18,
        mode=LEVEL_PROBE_FAULT,
        d=0.0,
        ast_verified=True,
    )
    status_slow = f_slow.update_joint(
        passed=True,
        time_to_green_sec=120.0,
        edit_distance_ratio=0.18,
        mode=LEVEL_PROBE_FAULT,
        d=0.0,
        ast_verified=True,
    )

    mu_fast = float(f_fast.summary().mean[0])
    mu_slow = float(f_slow.summary().mean[0])

    assert status_fast == "VERIFIED_PASS"
    assert status_slow == "VERIFIED_PASS"
    assert mu_fast > mu_slow + 0.20, f"Expected mu_fast ({mu_fast}) > mu_slow ({mu_slow}) + 0.20"


def test_unverified_pass_with_zero_diff_blocks_skill_inflation():
    """If passed == True during LEVEL_PROBE_FAULT but edit_distance_ratio == 0.0, flag UNVERIFIED_PASS."""
    filt = SkillFilter(1, GRID, c_grid=(0.0, 0.1, 0.2, 0.3, 0.4), robust_drift=True)
    mu_before = float(filt.summary().mean[0])

    status = filt.update_joint(
        passed=True,
        time_to_green_sec=10.0,
        edit_distance_ratio=0.0,
        mode=LEVEL_PROBE_FAULT,
        d=0.0,
        ast_verified=False,
    )
    mu_after = float(filt.summary().mean[0])

    assert status == "UNVERIFIED_PASS"
    assert np.isclose(mu_after, mu_before, atol=1e-9)


def test_copy_paste_anomaly_blocks_false_skill_inflation():
    """Sub-3s skeleton completion or >25 chars/sec triggers ANOMALY_PASTE_SUSPECTED and zero skill gain."""
    filt = SkillFilter(1, GRID, c_grid=(0.0, 0.1, 0.2, 0.3, 0.4), robust_drift=True)
    mu_before = float(filt.summary().mean[0])
    c_before = float(filt.summary().c_mean[0])

    status = filt.update_joint(
        passed=True,
        time_to_green_sec=1.2,
        edit_distance_ratio=0.45,
        mode=LEVEL_SKELETON,
        d=0.0,
        ast_verified=True,
        chars_per_sec=140.0,
    )
    summ_after = filt.summary()
    mu_after = float(summ_after.mean[0])
    c_after = float(summ_after.c_mean[0])

    assert status == "ANOMALY_PASTE_SUSPECTED"
    assert np.isclose(mu_after, mu_before, atol=1e-9)
    assert c_after > c_before
