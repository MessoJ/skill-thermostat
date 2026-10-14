"""Item difficulty calibration from pilot data."""
import argparse
import json
import sqlite3
import sys

import numpy as np
from scipy.special import ndtr
from scipy.stats import norm

from skill_thermostat.model import A_DISC, GRID

MIN_N = 30
D_CAND = np.linspace(-3.5, 3.5, 281)


def load_responses(db_path):
    con = sqlite3.connect(db_path)
    rows = con.execute("SELECT user, ex_id, passed FROM tasks WHERE done IS NOT NULL AND off=1 AND suspect=0").fetchall()
    con.close()
    return [(u, e, int(p)) for u, e, p in rows]


def _refine_d(n_g, r_g, d_init, d0, prior_sd, a, steps=5):
    """Continuous Newton-Raphson refinement of MAP item difficulty d and analytical curvature."""
    d = float(d_init)
    for _ in range(steps):
        z = a * (GRID - d)
        p = np.clip(ndtr(z), 1e-9, 1.0 - 1e-9)
        phi = np.exp(-0.5 * z ** 2) / np.sqrt(2.0 * np.pi)
        w1 = a * phi / (p * (1.0 - p))
        grad = -np.sum((r_g - n_g * p) * w1) - (d - d0) / (prior_sd ** 2)
        # Fisher scoring (expected negative Hessian) is strictly positive-definite
        info = np.sum(n_g * (a * phi) ** 2 / (p * (1.0 - p))) + 1.0 / (prior_sd ** 2)
        step = np.clip(grad / info, -0.5, 0.5)
        d = float(np.clip(d + step, -3.5, 3.5))
        if abs(step) < 1e-6:
            break
    return d, info


def calibrate(responses, nominal, prior_sd=1.0, iters=40, a=A_DISC):
    """responses: iterable of (person, item, 0/1). nominal: {item: nominal d}. Returns {item: dict(d, se, n)}."""
    persons = sorted({p for p, _, _ in responses})
    items = sorted({i for _, i, _ in responses})
    pi = {p: k for k, p in enumerate(persons)}
    ii = {i: k for k, i in enumerate(items)}
    P, J, G = len(persons), len(items), len(GRID)
    y = np.full((P, J), -1, dtype=int)
    for p, i, r in responses:
        y[pi[p], ii[i]] = r
    d = np.array([nominal.get(i, 0.0) for i in items], dtype=float)
    d0 = d.copy()
    prior = norm.pdf(GRID)
    prior /= prior.sum()
    answered = y >= 0
    pc_cand = np.clip(ndtr(a * (GRID[None, :] - D_CAND[:, None])), 1e-9, 1.0 - 1e-9)
    log_pc, log_1pc = np.log(pc_cand), np.log(1.0 - pc_cand)
    infos = np.zeros(J)

    for _ in range(iters):
        p_ok = np.clip(ndtr(a * (GRID[None, :] - d[:, None])), 1e-9, 1.0 - 1e-9)
        logp, log1p = np.log(p_ok), np.log(1.0 - p_ok)
        ll = np.zeros((P, G))
        for j in range(J):
            m = answered[:, j]
            ll[m] += np.where(y[m, j][:, None] == 1, logp[j][None, :], log1p[j][None, :])
        w = np.exp(ll - ll.max(axis=1, keepdims=True)) * prior[None, :]
        w /= w.sum(axis=1, keepdims=True)
        new = d.copy()
        for j in range(J):
            m = answered[:, j]
            n_g = w[m].sum(axis=0)
            r_g = (w[m] * y[m, j][:, None]).sum(axis=0)
            obj = (r_g * log_pc + (n_g - r_g) * log_1pc).sum(axis=1) + norm.logpdf(D_CAND, d0[j], prior_sd)
            d_grid = D_CAND[int(np.argmax(obj))]
            new[j], infos[j] = _refine_d(n_g, r_g, d_grid, d0[j], prior_sd, a)
        if np.max(np.abs(new - d)) < 1e-4:
            d = new
            break
        d = new

    out = {}
    for j, item in enumerate(items):
        m = answered[:, j]
        out[item] = dict(d=float(d[j]), se=float(1.0 / np.sqrt(infos[j])) if infos[j] > 1e-9 else None,
                         n=int(m.sum()), nominal=float(d0[j]))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--out", default="pilot/calibrated.json")
    ap.add_argument("--prior-sd", type=float, default=1.0)
    a = ap.parse_args(argv)
    from . import exercises as X
    resp = load_responses(a.db)
    if not resp:
        sys.exit("no unassisted responses in the database yet")
    res = calibrate(resp, {e.id: e.d for e in X.ALL}, a.prior_sd)
    thin = [k for k, v in res.items() if v["n"] < MIN_N]
    keep = {k: v for k, v in res.items() if v["n"] >= MIN_N}
    with open(a.out, "w") as f:
        json.dump(dict(items={k: round(v["d"], 3) for k, v in keep.items()}, detail=res), f, indent=1)
    shift = [abs(v["d"] - v["nominal"]) for v in keep.values()]
    print(f"{len(resp)} responses, {len(res)} items; {len(keep)} with n>={MIN_N} written to {a.out}")
    if shift:
        print(f"mean |calibrated - nominal| = {np.mean(shift):.2f}, max {np.max(shift):.2f}")
    if thin:
        print(f"{len(thin)} items have fewer than {MIN_N} responses and keep their nominal difficulty")


if __name__ == "__main__":
    main()
