"""Item difficulty calibration from pilot data.

    python -m pilot.calibrate study.db --out pilot/calibrated.json [--prior-sd 1.0]

Model: P(correct) = Phi(A * (theta - d)), the same probit curve the thermostat uses, slope A fixed at model.A_DISC. People are
integrated out with a N(0, 1) prior (marginal maximum likelihood by EM on the filter's grid), so difficulties land on the scale
where the population mean skill is 0 and the sd is 1. Each difficulty gets a weak normal prior centred on the nominal guess
(default sd 1.0) so items with little data stay near their guess instead of running off.

Only unassisted responses count: tier 'off' and not flagged suspect. Items with fewer than MIN_N responses are reported but
should not replace the nominal value. Nothing here is validated on real data yet; the recovery test uses simulated learners.
"""
import argparse
import json
import sqlite3
import sys
from collections import defaultdict

import numpy as np
from scipy.stats import norm

from skill_thermostat.model import A_DISC, GRID

MIN_N = 30
D_CAND = np.linspace(-3.5, 3.5, 281)


def load_responses(db_path):
    con = sqlite3.connect(db_path)
    rows = con.execute("SELECT user, ex_id, passed FROM tasks WHERE done IS NOT NULL AND off=1 AND suspect=0").fetchall()
    con.close()
    return [(u, e, int(p)) for u, e, p in rows]


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
    for _ in range(iters):
        p_ok = norm.cdf(a * (GRID[None, :] - d[:, None]))                       # (J, G)
        logp, log1p = np.log(np.clip(p_ok, 1e-9, 1)), np.log(np.clip(1 - p_ok, 1e-9, 1))
        ll = np.zeros((P, G))
        for j in range(J):
            m = answered[:, j]
            ll[m] += np.where(y[m, j][:, None] == 1, logp[j][None, :], log1p[j][None, :])
        w = np.exp(ll - ll.max(axis=1, keepdims=True)) * prior[None, :]
        w /= w.sum(axis=1, keepdims=True)                                          # posterior over theta per person
        new = d.copy()
        for j in range(J):
            m = answered[:, j]
            n_g = w[m].sum(axis=0)                                                 # expected people at each theta
            r_g = (w[m] * y[m, j][:, None]).sum(axis=0)                            # expected correct at each theta
            pc = norm.cdf(a * (GRID[None, :] - D_CAND[:, None]))                   # (candidates, G)
            obj = (r_g * np.log(np.clip(pc, 1e-9, 1)) + (n_g - r_g) * np.log(np.clip(1 - pc, 1e-9, 1))).sum(axis=1)
            obj += norm.logpdf(D_CAND, d0[j], prior_sd)
            new[j] = D_CAND[int(np.argmax(obj))]
        if np.max(np.abs(new - d)) < 1e-3:
            d = new
            break
        d = new
    out, step = {}, D_CAND[1] - D_CAND[0]
    for j, item in enumerate(items):
        m = answered[:, j]
        n_g, r_g = w[m].sum(axis=0), (w[m] * y[m, j][:, None]).sum(axis=0)
        pc = norm.cdf(a * (GRID[None, :] - D_CAND[:, None]))
        obj = (r_g * np.log(np.clip(pc, 1e-9, 1)) + (n_g - r_g) * np.log(np.clip(1 - pc, 1e-9, 1))).sum(axis=1)
        obj += norm.logpdf(D_CAND, d0[j], prior_sd)
        k = int(np.clip(np.argmax(obj), 1, len(D_CAND) - 2))
        curv = -(obj[k + 1] - 2 * obj[k] + obj[k - 1]) / step ** 2
        out[item] = dict(d=float(d[j]), se=float(1 / np.sqrt(curv)) if curv > 1e-9 else None, n=int(m.sum()),
                         nominal=float(d0[j]))
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
    json.dump(dict(items={k: round(v["d"], 3) for k, v in keep.items()}, detail=res), open(a.out, "w"), indent=1)
    shift = [abs(v["d"] - v["nominal"]) for v in keep.values()]
    print(f"{len(resp)} responses, {len(res)} items; {len(keep)} with n>={MIN_N} written to {a.out}")
    if shift:
        print(f"mean |calibrated - nominal| = {np.mean(shift):.2f}, max {np.max(shift):.2f}")
    if thin:
        print(f"{len(thin)} items have fewer than {MIN_N} responses and keep their nominal difficulty")


if __name__ == "__main__":
    main()
