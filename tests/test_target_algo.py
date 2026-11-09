"""Real pytest suite validating all 4 primitives in workspace/target_algo.py.

When an active LEVEL_SKELETON or LEVEL_PROBE_FAULT mutates `workspace/target_algo.py`
on disk, this test suite genuinely fails until the developer repairs the code.
"""
from __future__ import annotations

import pytest

from workspace.target_algo import (
    bisect_threshold,
    clamp_assistance_gain,
    ewma_variance,
    rolling_breach_rate,
    token_bucket_allow,
)


def test_bisect_threshold_exact_and_boundary_cases():
    assert bisect_threshold([], 1.0) == 0
    assert bisect_threshold([1.0, 2.0, 3.0, 4.0], 2.5) == 2
    assert bisect_threshold([1.0, 2.0, 2.0, 3.0], 2.0) == 1
    assert bisect_threshold([1.0, 2.0, 3.0], 0.5) == 0
    assert bisect_threshold([1.0, 2.0, 3.0], 9.0) == 3


def test_rolling_breach_rate_window_and_bounds():
    assert rolling_breach_rate([], -0.25, window=5) == 0.0
    assert rolling_breach_rate([-0.5, -0.4, 0.1], -0.25, window=0) == 0.0
    assert rolling_breach_rate([-0.5, -0.4, 0.1], -0.25, window=-2) == 0.0
    scores = [0.2, -0.3, -0.4, 0.1, -0.2, -0.5]
    assert abs(rolling_breach_rate(scores, -0.25, window=4) - 0.5) < 1e-9
    # Boundary equality: score == floor is NOT a breach
    assert rolling_breach_rate([-0.25, -0.25], -0.25, window=2) == 0.0


def test_token_bucket_allow_boundary_and_refill():
    # Exact boundary: available == cost (2.0 == 2.0) must be allowed
    allowed, rem = token_bucket_allow(tokens=1.0, capacity=5.0, refill_rate=0.5, elapsed_sec=2.0, cost=2.0)
    assert allowed is True and abs(rem - 0.0) < 1e-9

    allowed_cap, rem_cap = token_bucket_allow(tokens=4.0, capacity=5.0, refill_rate=2.0, elapsed_sec=3.0, cost=3.0)
    assert allowed_cap is True and abs(rem_cap - 2.0) < 1e-9

    denied, rem_den = token_bucket_allow(tokens=0.5, capacity=5.0, refill_rate=0.5, elapsed_sec=1.0, cost=2.0)
    assert denied is False and abs(rem_den - 1.0) < 1e-9


def test_ewma_variance_step_and_constant_series():
    assert ewma_variance([], 0.25) == 0.0
    assert ewma_variance([4.2], 0.25) == 0.0
    assert abs(ewma_variance([0.0, 4.0], alpha=0.25) - 3.0) < 1e-9
    assert abs(ewma_variance([3.0, 3.0, 3.0, 3.0], alpha=0.25)) < 1e-12
    v = ewma_variance([0.0, 4.0, 0.0, 4.0], alpha=0.25)
    assert abs(v - 3.80859375) < 1e-6


def test_clamp_assistance_gain_margins():
    with pytest.raises(ValueError):
        clamp_assistance_gain(0.0, 0.0, m_lo=0.2, m_hi=0.1)
    assert clamp_assistance_gain(-0.40, -0.25) == 0.0
    assert clamp_assistance_gain(0.10, -0.25) == 1.0
    mid = clamp_assistance_gain(-0.175, -0.25)
    assert abs(mid - 0.5) < 1e-9
