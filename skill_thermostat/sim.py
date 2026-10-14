"""Toy simulator: four hand-built worlds, eight assistance policies.

Demonstrates mechanics only. The worlds are assumptions, not evidence about real people,
and the controller thresholds were set by hand.

    python -m skill_thermostat.sim [--quick] [--seeds 100,101,102]
"""
import argparse
from dataclasses import dataclass, replace

import numpy as np

from .controller import Thermostat, ThermostatConfig
from .filters import SkillFilter
from .model import CAP, GRID, PHYS_FLOOR, SPEED, p_assisted, p_solo
from .model import Q_AI  # noqa: F401  (re-exported for convenience)

S_MAX = 0.5          # tasks with stakes above this are never probed or withheld
DELTA = 0.40         # tolerated drop in unassisted skill (floor = baseline - DELTA)
K0 = 30              # trusted AI-off baseline items per worker
C_GRID = (0.0, 0.1, 0.2, 0.3, 0.4)
SENTINEL_RATE = 0.03


@dataclass(frozen=True)
class World:
    name: str
    lam: float          # learning rate from effortful work
    lam_review: float   # learning from reviewing AI output (scales with existing skill)
    decay: float        # disuse decay rate
    om_jun: tuple       # Beta(a,b) for offloading propensity, juniors
    om_sen: tuple       # Beta(a,b) for offloading propensity, seniors
    contam: float = 0.0  # P(an ordinary "AI-off" task is secretly assisted by another tool)


WORLDS = [
    World("W1 benign (no atrophy)", 0.006, 0.004, 0.000, (2, 5), (2, 5)),
    World("W2 atrophy",             0.006, 0.000, 0.003, (5, 2), (5, 2)),
    World("W3 bifurcated",          0.006, 0.006, 0.003, (5, 1.5), (2, 5)),
    World("W4 severe atrophy",      0.006, 0.000, 0.007, (6, 1.5), (6, 1.5)),
]
POLICIES = ["always_on", "never_ai", "fixed_drills", "random_10", "zpd_oracle",
            "thermostat", "thermostat_robust", "thermostat_oracle"]


def simulate(world, policy, seed, N, T, cfg=None, wide_shift=-0.04, wide_sd=0.08, arg=None):
    """arg tunes the baselines: drill period (fixed_drills), AI-off probability (random_10),
    constant assistance level (fixed_alpha). cfg/wide_shift/wide_sd tune the thermostat."""
    rng = np.random.default_rng(seed)       # same seed -> same workers and tasks for every policy
    senior = rng.random(N) < 0.5
    th0 = np.where(senior, rng.normal(0.9, 0.35, N), rng.normal(-0.4, 0.35, N))
    om = np.where(senior, rng.beta(*world.om_sen, N), rng.beta(*world.om_jun, N))
    d = rng.normal(0.0, 0.9, (N, T))        # task difficulty
    s = rng.beta(1, 4, (N, T))              # task stakes (mostly low)
    u_succ, u_probe, u_cont = rng.random((3, N, T))
    anc_d = rng.normal(0.0, 0.8, (N, K0))
    anc_u = rng.random((N, K0))
    u_sent = rng.random((N, T))             # drawn last so every earlier stream matches v0

    robust = policy == "thermostat_robust"
    use_f = policy in ("thermostat", "thermostat_robust")
    if cfg is None:
        cfg = ThermostatConfig(sentinel_rate=SENTINEL_RATE if robust else 0.0)
    if use_f:                               # trusted baseline assessment -> prior + personal floor
        F = SkillFilter(N, GRID, c_grid=C_GRID if robust else (0.0,), robust_drift=robust,
                        wide_shift=wide_shift, wide_sd=wide_sd)
        ctl = Thermostat(cfg, GRID)
        ones = np.ones(N, bool)
        for k in range(K0):
            y0 = anc_u[:, k] < p_solo(th0, anc_d[:, k])
            F.update(anc_d[:, k], y0, ones, trusted=ones)
        floor_hat = F.summary().mean - DELTA
        ae_acc = np.zeros(N)

    th, floor_true = th0.copy(), th0 - DELTA
    prod = np.zeros((T, N))
    viol = np.zeros((T, N), bool)
    offl = np.zeros((T, N), bool)
    cov = np.zeros((T, N), bool)

    for t in range(T):
        dt = d[:, t]
        elig = s[:, t] <= S_MAX             # high-stakes tasks always get full AI, never probed
        sent = np.zeros(N, bool)
        if policy == "always_on":
            alpha, off = np.ones(N), np.zeros(N, bool)
        elif policy == "never_ai":
            alpha, off = np.zeros(N), np.ones(N, bool)
        elif policy == "fixed_drills":      # AI-off on every k-th eligible task (default k=5)
            alpha, off = np.ones(N), elig & (t % (int(arg) if arg else 5) == 0)
        elif policy == "random_10":         # non-adaptive random AI-off (default p=0.10)
            alpha, off = np.ones(N), elig & (u_probe[:, t] < (0.10 if arg is None else arg))
        elif policy == "fixed_alpha":       # constant partial assistance, no measurement at all
            alpha, off = np.where(elig, arg, 1.0), np.zeros(N, bool)
        elif policy == "zpd_oracle":        # PSN-inspired: withdraw help near true skill (cheats: sees truth)
            phi = np.exp(-(dt - th - 0.3) ** 2 / (2 * 0.8 ** 2))
            alpha, off = np.where(elig, 1.0 - phi, 1.0), np.zeros(N, bool)
        elif policy == "thermostat_oracle":  # same control rule, sees true skill, needs no probes
            c0 = ThermostatConfig()
            a = np.clip(((th - floor_true) - c0.m_lo) / (c0.m_hi - c0.m_lo), 0, 1)
            off = elig & (a <= 0)
            alpha = np.where(elig, a, 1.0)
        else:                               # thermostat: measure with probes, steer on the lower bound
            summ = F.summary()
            alpha, off, sent = ctl.decide(summ, floor_hat, elig, u_probe[:, t], u_sent[:, t])
            cov[t] = th >= summ.q10

        ae = np.where(off, 0.0, alpha)      # effective assistance this task
        pu = p_solo(th, dt)
        prod[t] = (1.0 + SPEED * ae) * (1.0 - (1.0 - pu) * (1.0 - ae * Q_AI))

        if use_f:                           # unassisted outcomes feed the filter
            cont = off & ~sent & (u_cont[:, t] < world.contam)
            p_obs = np.where(cont, p_assisted(pu), pu)
            F.update(dt, u_succ[:, t] < p_obs, off, trusted=sent)
            ae_acc += ae
            if (t + 1) % 10 == 0:
                F.predict(wide=(ae_acc / 10 > 0.5) if robust else None)
                ae_acc[:] = 0.0

        e = 1.0 - ae * om                   # share of the cognitive work the human did
        g = np.exp(-(dt - th - 0.3) ** 2 / (2 * 0.8 ** 2))   # zone-of-proximal-development fit
        room = (CAP - th) / (CAP - PHYS_FLOOR)
        dth = (world.lam * e * g * room
               + world.lam_review * ae * g * np.clip(th, 0, None) / CAP * room
               - world.decay * (1.0 - e) * np.clip(th - PHYS_FLOOR, 0, 1))
        th = np.clip(th + dth, PHYS_FLOOR - 0.5, CAP)
        viol[t] = th < floor_true
        offl[t] = off

    return dict(prod=prod.mean(), viol=viol.mean(), off=offl.mean(),
                d_jun=(th - th0)[~senior].mean(), d_sen=(th - th0)[senior].mean(),
                cov=cov.mean() if use_f else np.nan,
                c_hat=float(F.summary().c_mean.mean()) if use_f else np.nan)


def _fmt(x, pct=False):
    if np.isnan(x):
        return "-"
    return f"{100 * x:.1f}" if pct else f"{x:.3f}"


def run(seeds, N, T):
    for w in WORLDS:
        rows = {p: [] for p in POLICIES}
        for sd in seeds:
            base = None
            for p in POLICIES:
                r = simulate(w, p, sd, N, T)
                if p == "always_on":
                    base = r["prod"]
                r["prod_rel"] = r["prod"] / base
                rows[p].append(r)
        print(f"\n== {w.name} ==")
        print(f"{'policy':<19}{'prod_rel':>9}{'viol%':>7}{'AIoff%':>8}{'dSk_jun':>9}{'dSk_sen':>9}{'q10cov%':>9}")
        for p in POLICIES:
            m = {k: float(np.mean([r[k] for r in rows[p]])) for k in rows[p][0]}
            print(f"{p:<19}{_fmt(m['prod_rel']):>9}{_fmt(m['viol'], True):>7}{_fmt(m['off'], True):>8}"
                  f"{m['d_jun']:>9.2f}{m['d_sen']:>9.2f}{_fmt(m['cov'], True):>9}")


def contamination(seeds, N, T):
    w0 = WORLDS[2]
    print("\n== Contamination (W3 bifurcated): share of ordinary AI-off tasks secretly AI-assisted ==")
    print(f"{'policy':<19}{'contam':<8}{'prod_rel':>9}{'viol%':>7}{'q10cov%':>9}{'c_hat%':>8}")
    for p in ("thermostat", "thermostat_robust"):
        for c in (0.0, 0.15, 0.30):
            out = []
            for sd in seeds:
                base = simulate(w0, "always_on", sd, N, T)["prod"]
                r = simulate(replace(w0, contam=c), p, sd, N, T)
                r["prod_rel"] = r["prod"] / base
                out.append(r)
            m = {k: float(np.mean([r[k] for r in out])) for k in out[0]}
            print(f"{p:<19}{c:<8}{_fmt(m['prod_rel']):>9}{_fmt(m['viol'], True):>7}"
                  f"{_fmt(m['cov'], True):>9}{_fmt(m['c_hat'], True):>8}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--seeds", default="100,101,102")
    a = ap.parse_args()
    seeds = [int(x) for x in a.seeds.split(",")]
    N, T = (100, 200) if a.quick else (400, 400)
    if a.quick:
        seeds = seeds[:1]
    run(seeds, N, T)
    contamination(seeds, N, T)
    print("\nToy model. Worlds are assumptions; thresholds hand-set. Mechanics only, not evidence about people.")


if __name__ == "__main__":
    main()
