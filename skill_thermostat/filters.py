"""Bayesian grid filter over (latent skill, probe-contamination rate) per worker and domain."""
from __future__ import annotations

import numpy as np
from scipy.special import ndtr

from .controller import Summary
from .model import A_DISC, Q_AI, joint_observation_likelihood


def _kernel(grid, shift, sd):
    diff = grid[None, :] - grid[:, None] - shift
    K = np.exp(-0.5 * (diff / sd) ** 2)
    return K / K.sum(1, keepdims=True)


def _interp_quantile(grid, cdf, q=0.10):
    """Sub-grid linear interpolation of the q-th quantile from a discrete CDF (N, G)."""
    n, g = cdf.shape
    idx = np.clip((cdf < q).sum(1), 0, g - 1)
    lo = np.maximum(idx - 1, 0)
    c_hi = cdf[np.arange(n), idx]
    c_lo = np.where(idx > 0, cdf[np.arange(n), lo], 0.0)
    denom = np.where(c_hi > c_lo, c_hi - c_lo, 1.0)
    frac = np.clip((q - c_lo) / denom, 0.0, 1.0)
    g_lo = np.where(idx > 0, grid[lo], grid[0])
    return g_lo + frac * (grid[idx] - g_lo)


class SkillFilter:
    def __init__(self, n, grid, c_grid=(0.0,), prior_sd=1.5, q_sd=0.047,
                 robust_drift=False, wide_shift=-0.04, wide_sd=0.08,
                 learn_shift=0.015, a_disc=A_DISC, q_ai=Q_AI, prior_mean=0.0):
        self.grid = np.asarray(grid, float)
        self.c = np.asarray(c_grid, float)
        self.a, self.q = a_disc, q_ai
        row = np.exp(-0.5 * ((self.grid - float(prior_mean)) / prior_sd) ** 2)
        row /= row.sum()
        c_prior = np.full(len(self.c), 1.0 / len(self.c))
        self.post = np.tile(row[None, :, None] * c_prior[None, None, :], (n, 1, 1))
        self.K = _kernel(self.grid, 0.0, q_sd)
        self.K_learn = _kernel(self.grid, learn_shift, q_sd) if robust_drift else self.K
        self.Kw = _kernel(self.grid, wide_shift, wide_sd) if robust_drift else self.K

    def predict(self, wide=None, learning=None):
        """Random-walk drift between observations; `wide` marks heavily-assisted workers,
        `learning` marks workers doing primarily unassisted effortful practice."""
        out = np.matmul(self.K.T, self.post)
        if learning is not None and np.any(learning):
            idx_l = np.flatnonzero(learning)
            out[idx_l] = np.matmul(self.K_learn.T, self.post[idx_l])
        if wide is not None and np.any(wide):
            idx = np.flatnonzero(wide)
            out[idx] = np.matmul(self.Kw.T, self.post[idx])
        self.post = out / out.sum((1, 2), keepdims=True)

    def update(self, d, y, mask, trusted=None):
        """d: task difficulty per worker; y: success on an AI-off task; mask: who was observed."""
        idx = np.flatnonzero(mask)
        if idx.size == 0:
            return
        pm = ndtr(self.a * (self.grid[None, :] - d[idx, None]))           # (k, G) clean success
        pc = 1.0 - (1.0 - pm) * (1.0 - self.q)                            # (k, G) if secretly assisted
        c = self.c[None, None, :]
        ps = (1.0 - c) * pm[:, :, None] + c * pc[:, :, None]              # (k, G, C)
        if trusted is not None:
            ps = np.where(trusted[idx][:, None, None], pm[:, :, None], ps)
        lik = np.where(y[idx][:, None, None], ps, 1.0 - ps) + 1e-12
        sub = self.post[idx] * lik
        self.post[idx] = sub / sub.sum((1, 2), keepdims=True)

    def update_joint(
        self,
        passed: bool,
        time_to_green_sec: float,
        edit_distance_ratio: float,
        mode: str,
        d: float = 0.0,
        ast_verified: bool = True,
        chars_per_sec: float | None = None,
        trusted: bool = True,
        huber_damping: bool = True,
        worker_idx: int = 0,
    ) -> str:
        """Update worker posterior from joint tuple `(passed, time_to_green_sec, edit_distance_ratio, mode)`."""
        lik_clean, lik_contam, status_flag = joint_observation_likelihood(
            theta=self.grid,
            passed=bool(passed),
            time_to_green_sec=float(time_to_green_sec),
            edit_distance_ratio=float(edit_distance_ratio),
            mode=str(mode),
            d=float(d),
            ast_verified=bool(ast_verified),
            chars_per_sec=chars_per_sec,
            huber_damping=bool(huber_damping),
            a=self.a,
            q=self.q,
        )

        if status_flag == "UNVERIFIED_PASS":
            return status_flag

        if status_flag == "ANOMALY_PASTE_SUSPECTED":
            if len(self.c) > 1:
                c_boost = np.linspace(0.5, 1.8, len(self.c))[None, :]
                sub = self.post[worker_idx] * c_boost
                self.post[worker_idx] = sub / sub.sum()
            return status_flag

        c = self.c[None, :]  # (1, C)
        if trusted:
            lik_2d = lik_clean[:, None] * np.ones_like(c)
        else:
            lik_2d = (1.0 - c) * lik_clean[:, None] + c * lik_contam[:, None]

        sub = self.post[worker_idx] * (lik_2d + 1e-12)
        self.post[worker_idx] = sub / sub.sum()
        return status_flag

    def summary(self):
        pg = self.post.sum(2)
        mean = pg @ self.grid
        sd = np.sqrt(np.maximum(pg @ self.grid ** 2 - mean ** 2, 1e-12))
        cdf = np.cumsum(pg, 1)
        q10 = _interp_quantile(self.grid, cdf, 0.10)
        c_mean = self.post.sum(1) @ self.c
        return Summary(mean, sd, q10, cdf, c_mean)


class MultiDomainSkillFilter:
    """Maintains independent `SkillFilter` posteriors per domain while sharing a weak global hyper-prior."""

    def __init__(
        self,
        grid=None,
        c_grid=(0.0, 0.1, 0.2, 0.3, 0.4),
        prior_sd: float = 1.5,
        hyper_weight: float = 0.15,
    ) -> None:
        from .model import GRID as DEFAULT_GRID

        self.grid = np.asarray(grid if grid is not None else DEFAULT_GRID, dtype=float)
        self.c_grid = tuple(c_grid)
        self.prior_sd = float(prior_sd)
        self.hyper_weight = float(hyper_weight)
        self.domains: dict[str, SkillFilter] = {}

    def global_hyper_mean(self) -> float:
        """Compute weakly-coupled hyper-prior mean across established domains."""
        if not self.domains:
            return 0.0
        means = [float(f.summary().mean[0]) for f in self.domains.values()]
        return float(self.hyper_weight * np.mean(means))

    def get_domain_filter(self, domain: str = "py:algo") -> SkillFilter:
        key = str(domain or "py:algo")
        if key not in self.domains:
            hyper_mu = self.global_hyper_mean()
            self.domains[key] = SkillFilter(
                1,
                self.grid,
                c_grid=self.c_grid,
                prior_sd=self.prior_sd,
                robust_drift=True,
                prior_mean=hyper_mu,
            )
        return self.domains[key]
