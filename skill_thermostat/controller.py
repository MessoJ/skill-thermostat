"""The thermostat: turns a skill posterior into (assistance level, AI-off flag) for the next task."""
from dataclasses import dataclass
from typing import NamedTuple

import numpy as np

from .model import GRID


class Summary(NamedTuple):
    mean: np.ndarray    # posterior mean skill
    sd: np.ndarray      # posterior sd
    q10: np.ndarray     # 10th-percentile skill (the lower bound the controller steers on)
    cdf: np.ndarray     # posterior CDF over the skill grid
    c_mean: np.ndarray  # posterior mean probe-contamination rate


@dataclass(frozen=True)
class ThermostatConfig:
    m_lo: float = -0.05        # margin (lower bound minus floor) where assistance starts ramping up
    m_hi: float = 0.20         # margin where assistance is full
    pi_min: float = 0.04       # probe probability bounds
    pi_max: float = 0.60
    k_risk: float = 0.60       # probe-rate gain on P(skill near floor)
    k_unc: float = 0.25        # probe-rate gain on posterior uncertainty
    sd_target: float = 0.12
    risk_margin: float = 0.10  # "near floor" = within this of the floor
    sentinel_rate: float = 0.0  # share of eligible tasks run as trusted lockdown items


class Thermostat:
    def __init__(self, cfg=None, grid=GRID):
        self.cfg = cfg or ThermostatConfig()
        self.grid = np.asarray(grid, float)

    def decide(self, summ, floor_hat, elig, u_probe, u_sent):
        """Return (alpha, off, sentinel).

        alpha: assistance level in [0,1]; off: this task is AI-off (a probe or forced);
        sentinel: this AI-off task is a trusted lockdown item. Ineligible (high-stakes)
        tasks always get full assistance and are never probed.
        """
        c = self.cfg
        a = np.clip(((summ.q10 - floor_hat) - c.m_lo) / (c.m_hi - c.m_lo), 0.0, 1.0)
        j = np.clip(np.searchsorted(self.grid, floor_hat + c.risk_margin) - 1, 0, len(self.grid) - 1)
        risk = summ.cdf[np.arange(len(a)), j]
        pi = np.clip(c.pi_min + c.k_risk * risk
                     + c.k_unc * np.clip((summ.sd - c.sd_target) / 0.2, 0.0, 1.0), c.pi_min, c.pi_max)
        sent = elig & (u_sent < c.sentinel_rate)
        off = (elig & ((u_probe < pi) | (a <= 0))) | sent
        alpha = np.where(elig, a, 1.0)
        return alpha, off, sent
