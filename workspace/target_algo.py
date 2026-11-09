"""Target algorithmic module mutated on disk by Skill Thermostat interventions.

Contains 4 core algorithmic primitives cycled in the physical repair loop:
  1. `bisect_threshold`
  2. `rolling_breach_rate`
  3. `token_bucket_allow`
  4. `ewma_variance`
"""
from __future__ import annotations


def bisect_threshold(values: list[float], target: float) -> int:
    """Return the first index i where values[i] >= target, or len(values)."""
    lo = 0
    hi = len(values)
    while lo < hi:
        mid = (lo + hi) // 2
        if values[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    return lo


def rolling_breach_rate(scores: list[float], floor: float, window: int = 5) -> float:
    """Return fraction of scores in the trailing window strictly below floor."""
    if window <= 0 or not scores:
        return 0.0
    tail = scores[-window:]
    breaches = sum(1 for x in tail if x < floor)
    return breaches / len(tail)


def token_bucket_allow(
    tokens: float,
    capacity: float,
    refill_rate: float,
    elapsed_sec: float,
    cost: float = 1.0,
) -> tuple[bool, float]:
    """Refill token bucket over `elapsed_sec` and consume `cost` if available."""
    if elapsed_sec < 0.0:
        elapsed_sec = 0.0
    available = min(capacity, tokens + refill_rate * elapsed_sec)
    if available >= cost:
        return True, available - cost
    return False, available


def ewma_variance(samples: list[float], alpha: float = 0.25) -> float:
    """Compute exponentially weighted moving variance across `samples`."""
    if len(samples) < 2:
        return 0.0
    mean = samples[0]
    var = 0.0
    for x in samples[1:]:
        diff = x - mean
        incr = alpha * diff
        mean = mean + incr
        var = (1.0 - alpha) * (var + diff * incr)
    return var


def clamp_assistance_gain(
    q10: float, floor: float, m_lo: float = -0.05, m_hi: float = 0.20
) -> float:
    """Compute normalized assistance gain alpha in [0.0, 1.0]."""
    if m_hi <= m_lo:
        raise ValueError("m_hi must exceed m_lo")
    raw = ((q10 - floor) - m_lo) / (m_hi - m_lo)
    if raw < 0.0:
        return 0.0
    if raw > 1.0:
        return 1.0
    return raw
