"""The thermostat: turns a skill posterior into (assistance level, AI-off flag, discrete mode) for the next task."""
from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple

import numpy as np

from .model import GRID


class Summary(NamedTuple):
    mean: np.ndarray     # posterior mean skill
    sd: np.ndarray       # posterior sd
    q10: np.ndarray      # 10th-percentile skill (the lower bound the controller steers on)
    cdf: np.ndarray      # posterior CDF over the skill grid
    c_mean: np.ndarray   # posterior mean probe-contamination rate


@dataclass(frozen=True)
class ThermostatConfig:
    m_lo: float = -0.05         # margin (lower bound minus floor) where assistance starts ramping up
    m_hi: float = 0.20          # margin where assistance is full
    pi_min: float = 0.04        # probe probability bounds
    pi_max: float = 0.60
    k_risk: float = 0.60        # probe-rate gain on P(skill near floor)
    k_unc: float = 0.25         # probe-rate gain on posterior uncertainty
    sd_target: float = 0.12
    risk_margin: float = 0.10   # "near floor" = within this of the floor
    sentinel_rate: float = 0.0  # share of eligible tasks run as trusted lockdown items
    # Milestone 3 explicit 3-tier hysteresis thresholds on q10:
    floor_probe: float = -0.35  # q10 < floor_probe -> LEVEL_PROBE_FAULT
    floor_full: float = 0.25    # q10 >= floor_full -> LEVEL_FULL (with cadence K probe); between -> LEVEL_SKELETON
    probe_cadence: int = 5      # fire scheduled retention probe every K-th assisted task in LEVEL_FULL


class Thermostat:
    def __init__(self, cfg=None, grid=GRID):
        self.cfg = cfg or ThermostatConfig()
        self.grid = np.asarray(grid, float)

    def decide(self, summ, floor_hat, elig, u_probe, u_sent, since_last=None, stale_limit=10):
        """Return (alpha, off, sentinel).

        alpha: assistance level in [0,1]; off: this task is AI-off (a probe or forced);
        sentinel: this AI-off task is a trusted lockdown item. Ineligible (high-stakes)
        tasks always get full assistance and are never probed.
        """
        c = self.cfg
        floor_arr = np.asarray(floor_hat, float)
        a = np.clip(((summ.q10 - floor_arr) - c.m_lo) / (c.m_hi - c.m_lo), 0.0, 1.0)
        j = np.clip(np.searchsorted(self.grid, floor_arr + c.risk_margin, side="right") - 1, 0, len(self.grid) - 1)
        risk = summ.cdf[np.arange(len(a)), j]
        pi = np.clip(c.pi_min + c.k_risk * risk
                     + c.k_unc * np.clip((summ.sd - c.sd_target) / 0.2, 0.0, 1.0), c.pi_min, c.pi_max)
        if since_last is not None:
            sl = np.asarray(since_last, float)
            hazard = np.clip((sl - (stale_limit - 3)) / 3.0, 0.0, 1.0)
            pi = np.maximum(pi, hazard)
        sent = elig & (u_sent < c.sentinel_rate)
        off = (elig & ((u_probe < pi) | (a <= 0))) | sent
        alpha = np.where(elig, a, 1.0)
        return alpha, off, sent

    def decide_hysteresis(
        self,
        summ: Summary,
        since_last_probe: int = 0,
        floor_probe: float | None = None,
        floor_full: float | None = None,
        probe_cadence: int | None = None,
        worker_idx: int = 0,
    ) -> tuple[str, float, bool]:
        """Explicit 3-tier hysteresis controller using posterior 10th percentile `q10` and probe cadence.

        Tiers:
          - `LEVEL_FULL` when `q10 >= floor_full` (+0.25), firing a scheduled `LEVEL_PROBE_FAULT`
            every `probe_cadence` (K=5) consecutive assisted tasks to verify skill retention.
          - `LEVEL_SKELETON` (moderate scaffolding) when `floor_probe <= q10 < floor_full`
            (-0.35 <= q10 < +0.25).
          - `LEVEL_PROBE_FAULT` (diagnostic lock / unassisted verification) when
            `q10 < floor_probe` (< -0.35).

        Returns `(controller_level, alpha, is_probe)`.
        """
        c = self.cfg
        f_probe = c.floor_probe if floor_probe is None else float(floor_probe)
        f_full = c.floor_full if floor_full is None else float(floor_full)
        cadence = c.probe_cadence if probe_cadence is None else int(probe_cadence)

        q10_val = float(summ.q10[worker_idx])
        span = max(1e-6, f_full - f_probe)
        alpha = float(np.clip((q10_val - f_probe) / span, 0.0, 1.0))

        if q10_val < f_probe:
            return "LEVEL_PROBE_FAULT", 0.0, True

        if q10_val < f_full:
            return "LEVEL_SKELETON", alpha, False

        # q10_val >= f_full: eligible for LEVEL_FULL unless scheduled cadence probe is due
        if cadence > 0 and int(since_last_probe) >= cadence:
            return "LEVEL_PROBE_FAULT", 1.0, True

        return "LEVEL_FULL", 1.0, False
