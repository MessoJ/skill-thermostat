"""Shared constants and the joint probit + Huber-damped log-normal latency task-response model."""
from __future__ import annotations

import numpy as np
from scipy.special import ndtr  # standard normal CDF

A_DISC = 1.5          # slope of the probit task-response curve
Q_AI = 0.70           # P(AI rescues a failed attempt)
SPEED = 0.50          # throughput bonus from assistance
CAP = 3.0             # skill ceiling
PHYS_FLOOR = -1.5     # level that unused skill decays toward
GRID = np.linspace(-4.0, 4.0, 161)  # latent-skill grid used by the filter

# Log-normal latency & physical verification constants (Milestone 2 & 3)
TAU_0 = 30.0          # baseline median unassisted solve time (seconds) at (theta - d) = 0
BETA_LAT = 0.45       # log-time reduction per unit of latent skill margin (theta - d)
SIGMA_LAT = 0.70      # log-normal latency dispersion
GAMMA_LAT = 0.42      # latency likelihood weight relative to binary pass/fail probit
MAX_HUMAN_CPS = 25.0  # human typing/reading velocity upper bound (chars/sec) for unassisted skeleton
HUBER_TTG_SEC = 120.0 # circadian/fatigue threshold above which slow-pass penalty is Huber-capped


def p_solo(theta, d, a=A_DISC):
    """P(success) on a task of difficulty d with no assistance."""
    return ndtr(a * (theta - d))


def p_assisted(p, q=Q_AI):
    """P(success) when the AI also gets a chance to rescue a failed attempt."""
    return 1.0 - (1.0 - p) * (1.0 - q)


def lognormal_latency_factor(
    theta: np.ndarray,
    time_to_green_sec: float,
    d: float = 0.0,
    tau0: float = TAU_0,
    beta: float = BETA_LAT,
    sigma: float = SIGMA_LAT,
    gamma: float = GAMMA_LAT,
    huber_damping: bool = False,
) -> np.ndarray:
    """Log-normal time-to-green likelihood factor conditioned on latent skill `theta`.

    When `huber_damping=True` and `time_to_green_sec > HUBER_TTG_SEC` (120s) on a verified
    pass, applies a Huber-style cap to the positive log-latency residual `(log_t - mu_log_t)`
    so circadian fatigue slows upward skill growth without destroying established mastery `q10`.
    """
    t_clamped = float(np.clip(time_to_green_sec, 3.0, 600.0))
    if huber_damping and t_clamped > HUBER_TTG_SEC:
        # Cap effective slow-pass latency penalty at HUBER_TTG_SEC + logarithmic tail
        t_eff = HUBER_TTG_SEC + 15.0 * np.log1p((t_clamped - HUBER_TTG_SEC) / 60.0)
    else:
        t_eff = t_clamped

    log_t = np.log(t_eff)
    mu_log_t = np.log(tau0) - beta * (np.asarray(theta, dtype=float) - float(d))
    z = (log_t - mu_log_t) / sigma

    if huber_damping and t_clamped > HUBER_TTG_SEC:
        # Huber loss on slow tail (z > 0): linearize penalty beyond delta_h = 0.65
        delta_h = 0.65
        quad_or_huber = np.where(
            z > delta_h,
            delta_h * (2.0 * np.minimum(z, 1.25) - delta_h),
            z ** 2,
        )
        return np.exp(-0.5 * gamma * quad_or_huber)

    return np.exp(-0.5 * gamma * (z ** 2))


def joint_observation_likelihood(
    theta: np.ndarray,
    passed: bool,
    time_to_green_sec: float,
    edit_distance_ratio: float,
    mode: str,
    d: float = 0.0,
    ast_verified: bool = True,
    chars_per_sec: float | None = None,
    huber_damping: bool = True,
    a: float = A_DISC,
    q: float = Q_AI,
) -> tuple[np.ndarray, np.ndarray, str]:
    """Compute (clean_likelihood, secret_assist_likelihood, status_flag) over `theta` grid."""
    theta_arr = np.asarray(theta, dtype=float)
    ones = np.ones_like(theta_arr)
    is_probe_or_skel = mode in (
        "LEVEL_PROBE_FAULT",
        "LEVEL_SKELETON",
        "PROBE",
        "PROBE_UNASSISTED",
        "UNASSISTED",
    )

    if passed and is_probe_or_skel:
        if edit_distance_ratio <= 0.0 or not ast_verified:
            return ones, ones, "UNVERIFIED_PASS"

        if (chars_per_sec is not None and chars_per_sec > MAX_HUMAN_CPS) or (
            mode == "LEVEL_SKELETON" and time_to_green_sec < 3.0 and edit_distance_ratio >= 0.15
        ):
            return ones, ones, "ANOMALY_PASTE_SUSPECTED"

    pm_pass = p_solo(theta_arr, d, a=a)
    pc_pass = p_assisted(pm_pass, q=q)

    if passed:
        use_huber = bool(huber_damping and ast_verified and edit_distance_ratio > 0.0)
        lat_clean = lognormal_latency_factor(
            theta_arr, time_to_green_sec, d=d, huber_damping=use_huber
        )
        lat_contam = lognormal_latency_factor(
            theta_arr, time_to_green_sec, d=d - 0.5, huber_damping=use_huber
        )
        status = (
            "VERIFIED_PASS_FATIGUE_DAMPED"
            if (use_huber and time_to_green_sec > HUBER_TTG_SEC)
            else "VERIFIED_PASS"
        )
        return pm_pass * lat_clean, pc_pass * lat_contam, status

    return (1.0 - pm_pass), (1.0 - pc_pass), "FAILED"
