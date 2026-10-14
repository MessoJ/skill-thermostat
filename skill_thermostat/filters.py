"""Bayesian grid filter over (latent skill, probe-contamination rate) per worker.

Observations come from AI-off tasks. A *trusted* observation (a sentinel item or a
baseline anchor, administered under strict lockdown) is assumed uncontaminated and
therefore pins skill without touching the contamination estimate. An ordinary AI-off
probe may be secretly assisted with unknown probability c, so its likelihood is a
mixture; comparing probe results against trusted ones is what identifies c.
"""
import numpy as np
from scipy.special import ndtr

from .controller import Summary
from .model import A_DISC, Q_AI


def _kernel(grid, shift, sd):
    diff = grid[None, :] - grid[:, None] - shift
    K = np.exp(-0.5 * (diff / sd) ** 2)
    return K / K.sum(1, keepdims=True)


class SkillFilter:
    def __init__(self, n, grid, c_grid=(0.0,), prior_sd=1.5, q_sd=0.047,
                 robust_drift=False, wide_shift=-0.04, wide_sd=0.08,
                 a_disc=A_DISC, q_ai=Q_AI):
        self.grid = np.asarray(grid, float)
        self.c = np.asarray(c_grid, float)
        self.a, self.q = a_disc, q_ai
        row = np.exp(-0.5 * (self.grid / prior_sd) ** 2)
        row /= row.sum()
        c_prior = np.full(len(self.c), 1.0 / len(self.c))
        self.post = np.tile(row[None, :, None] * c_prior[None, None, :], (n, 1, 1))
        self.K = _kernel(self.grid, 0.0, q_sd)
        # Heavily assisted workers may be drifting down: use a wider, downward-biased kernel for them.
        self.Kw = _kernel(self.grid, wide_shift, wide_sd) if robust_drift else self.K

    def predict(self, wide=None):
        """Random-walk drift between observations; `wide` marks workers to use the wide kernel for."""
        out = np.matmul(self.K.T, self.post)
        if wide is not None and wide.any():
            idx = np.flatnonzero(wide)
            out[idx] = np.matmul(self.Kw.T, self.post[idx])
        self.post = out

    def update(self, d, y, mask, trusted=None):
        """d: task difficulty per worker; y: success on an AI-off task; mask: who was observed."""
        idx = np.flatnonzero(mask)
        if idx.size == 0:
            return
        pm = ndtr(self.a * (self.grid[None, :] - d[idx, None]))          # (k, G) clean success
        pc = 1.0 - (1.0 - pm) * (1.0 - self.q)                           # (k, G) if secretly assisted
        c = self.c[None, None, :]
        ps = (1.0 - c) * pm[:, :, None] + c * pc[:, :, None]             # (k, G, C)
        if trusted is not None:
            ps = np.where(trusted[idx][:, None, None], pm[:, :, None], ps)
        lik = np.where(y[idx][:, None, None], ps, 1.0 - ps) + 1e-12
        sub = self.post[idx] * lik
        self.post[idx] = sub / sub.sum((1, 2), keepdims=True)

    def summary(self):
        pg = self.post.sum(2)
        mean = pg @ self.grid
        sd = np.sqrt(np.maximum(pg @ self.grid ** 2 - mean ** 2, 1e-12))
        cdf = np.cumsum(pg, 1)
        q10 = self.grid[np.minimum((cdf < 0.10).sum(1), len(self.grid) - 1)]
        c_mean = self.post.sum(1) @ self.c
        return Summary(mean, sd, q10, cdf, c_mean)
