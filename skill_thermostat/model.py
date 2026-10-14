"""Shared constants and the task-response model."""
import numpy as np
from scipy.special import ndtr  # standard normal CDF

A_DISC = 1.5        # slope of the probit task-response curve
Q_AI = 0.70         # P(AI rescues a failed attempt)
SPEED = 0.50        # throughput bonus from assistance
CAP = 3.0           # skill ceiling
PHYS_FLOOR = -1.5   # level that unused skill decays toward
GRID = np.linspace(-4.0, 4.0, 161)  # latent-skill grid used by the filter


def p_solo(theta, d, a=A_DISC):
    """P(success) on a task of difficulty d with no assistance."""
    return ndtr(a * (theta - d))


def p_assisted(p, q=Q_AI):
    """P(success) when the AI also gets a chance to rescue a failed attempt."""
    return 1.0 - (1.0 - p) * (1.0 - q)
