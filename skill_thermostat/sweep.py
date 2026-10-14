"""Settings sweep: safety-vs-productivity frontier of the thermostat versus baselines.

    python -m skill_thermostat.sweep --out sweep_results.json

Configs are tuned on one set of seeds and the winners re-evaluated on fresh seeds, so the headline
numbers are not a selection artifact. The worlds are still hand-built assumptions, so this tunes the
thermostat to those assumptions, not to people.

Baselines include fixed_alpha (constant partial assistance, no measurement): the "just give less help"
alternative the thermostat has to beat to be worth its complexity.
"""
import argparse
import itertools
import json
import os
from dataclasses import replace
from multiprocessing import Pool

import numpy as np

from .controller import ThermostatConfig
from .sim import WORLDS, simulate

HARMFUL = (1, 2, 3)  # W2..W4: the worlds where AI use erodes skill
DRIFT = {"off": (0.0, 0.047), "std": (-0.04, 0.08), "strong": (-0.08, 0.12)}  # (wide_shift, wide_sd)
RAMPS = ((0.05, 0.30), (-0.05, 0.20), (-0.15, 0.10), (-0.25, 0.05))           # (m_lo, m_hi)


def thermostat_grid(quick=False):
    ramps = RAMPS[1::2] if quick else RAMPS
    out = []
    for (lo, hi), pm in itertools.product(ramps, (0.04, 0.10)):
        out.append(dict(name=f"basic  ramp=({lo:+.2f},{hi:+.2f}) pi_min={pm:.2f}", policy="thermostat",
                        cfg=dict(m_lo=lo, m_hi=hi, pi_min=pm),
                        default=((lo, hi) == (-0.05, 0.20) and pm == 0.04)))
    for (lo, hi), sent, dk in itertools.product(ramps, (0.01, 0.03), DRIFT):
        ws, wd = DRIFT[dk]
        out.append(dict(name=f"robust ramp=({lo:+.2f},{hi:+.2f}) sent={sent:.2f} drift={dk}",
                        policy="thermostat_robust", cfg=dict(m_lo=lo, m_hi=hi, sentinel_rate=sent),
                        wide_shift=ws, wide_sd=wd,
                        default=((lo, hi) == (-0.05, 0.20) and sent == 0.03 and dk == "std")))
    return out


def baseline_grid():
    out = [dict(name="always_on", policy="always_on"), dict(name="never_ai", policy="never_ai")]
    out += [dict(name=f"fixed_drills 1/{k}", policy="fixed_drills", arg=k) for k in (2, 3, 5, 10, 20)]
    out += [dict(name=f"random p={p:.2f}", policy="random_10", arg=p) for p in (0.05, 0.10, 0.20, 0.33, 0.50)]
    out += [dict(name=f"fixed_alpha a={a:.2f}", policy="fixed_alpha", arg=a) for a in (0.9, 0.75, 0.6, 0.45, 0.3)]
    return out


def _run(spec, world, seed, N, T):
    cfg = ThermostatConfig(**spec["cfg"]) if "cfg" in spec else None
    kw = {k: spec[k] for k in ("wide_shift", "wide_sd", "arg") if k in spec}
    return simulate(world, spec["policy"], seed, N, T, cfg=cfg, **kw)


def evaluate(job):
    spec, seeds, N, T = job
    worlds = list(WORLDS) + [replace(WORLDS[2], name="W3 contam30", contam=0.30)]
    per = {}
    for w in worlds:
        v, p = [], []
        for sd in seeds:
            base = simulate(w, "always_on", sd, N, T)["prod"]
            r = _run(spec, w, sd, N, T)
            v.append(r["viol"])
            p.append(r["prod"] / base)
        per[w.name] = (float(np.mean(v)), float(np.mean(p)))
    names = [w.name for w in WORLDS]
    return dict(name=spec["name"], spec=spec,
                viol=float(np.mean([per[names[i]][0] for i in HARMFUL])),
                viol_w4=per[names[3]][0], viol_contam=per["W3 contam30"][0],
                cost=float(1.0 - np.mean([per[n][1] for n in names])),
                cost_benign=float(1.0 - per[names[0]][1]), per=per)


def pareto(rows):
    """Non-dominated rows when minimizing (cost, viol)."""
    front, best = [], float("inf")
    for r in sorted(rows, key=lambda r: (r["cost"], r["viol"])):
        if r["viol"] < best - 1e-9:
            front.append(r)
            best = r["viol"]
    return front


def baseline_viol_at(cost, base_rows):
    xs, ys = zip(*sorted((r["cost"], r["viol"]) for r in pareto(base_rows)))
    return None if cost < xs[0] or cost > xs[-1] else float(np.interp(cost, xs, ys))


def table(rows, title, base_rows=None):
    print(f"\n{title}")
    print(f"{'config':<58}{'viol%':>7}{'w4%':>6}{'contam%':>9}{'cost%':>7}{'benign%':>9}"
          + ("  best_baseline_viol%@same_cost" if base_rows else ""))
    for r in rows:
        extra = ""
        if base_rows:
            b = baseline_viol_at(r["cost"], base_rows)
            extra = f"{100 * b:>14.1f}" if b is not None else f"{'n/a':>14}"
        print(f"{r['name']:<58}{100 * r['viol']:>7.1f}{100 * r['viol_w4']:>6.1f}{100 * r['viol_contam']:>9.1f}"
              f"{100 * r['cost']:>7.1f}{100 * r['cost_benign']:>9.1f}{extra}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tune", default="200,201")
    ap.add_argument("--valid", default="300,301,302")
    ap.add_argument("--n-tune", type=int, default=200)
    ap.add_argument("--t-tune", type=int, default=300)
    ap.add_argument("--n-valid", type=int, default=400)
    ap.add_argument("--t-valid", type=int, default=400)
    ap.add_argument("--out", default="sweep_results.json")
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    tune = [int(x) for x in a.tune.split(",")]
    valid = [int(x) for x in a.valid.split(",")]
    nt, tt, nv, tv = a.n_tune, a.t_tune, a.n_valid, a.t_valid
    if a.quick:
        tune, valid, nt, tt, nv, tv = tune[:1], valid[:1], 60, 100, 60, 100
    t_specs, b_specs = thermostat_grid(a.quick), baseline_grid()
    procs = os.cpu_count() or 1
    print(f"tuning {len(t_specs)} thermostat + {len(b_specs)} baseline configs on seeds {tune} "
          f"(N={nt}, T={tt}, {procs} procs)", flush=True)
    is_t = lambda r: r["spec"]["policy"].startswith("thermostat")  # noqa: E731
    with Pool(procs) as pool:
        rows = pool.map(evaluate, [(s, tune, nt, tt) for s in t_specs + b_specs], chunksize=1)
        t_rows, b_rows = [r for r in rows if is_t(r)], [r for r in rows if not is_t(r)]
        front = pareto(t_rows)
        table(front, f"TUNE seeds {tune}: thermostat Pareto frontier", b_rows)
        table(pareto(b_rows), f"TUNE seeds {tune}: baseline frontier")

        picks = []
        for target in (0.10, 0.20, 0.30):
            r = min(front, key=lambda x: abs(x["cost"] - target))
            if r["name"] not in [p["name"] for p in picks]:
                picks.append(r)
        if front[-1]["name"] not in [p["name"] for p in picks]:
            picks.append(front[-1])
        chosen = {p["name"]: p["spec"] for p in picks}
        chosen.update({r["name"]: r["spec"] for r in t_rows if r["spec"].get("default")})
        print(f"\nvalidating {len(chosen)} thermostat configs + {len(b_specs)} baselines on FRESH seeds {valid} "
              f"(N={nv}, T={tv})", flush=True)
        v_rows = pool.map(evaluate, [(s, valid, nv, tv) for s in list(chosen.values()) + b_specs], chunksize=1)

    vt, vb = [r for r in v_rows if is_t(r)], [r for r in v_rows if not is_t(r)]
    table(sorted(vt, key=lambda r: r["cost"]), f"VALIDATION seeds {valid}: chosen thermostat configs vs baselines", vb)
    table(sorted(vb, key=lambda r: r["cost"]), f"VALIDATION seeds {valid}: baselines")
    with open(a.out, "w") as f:
        json.dump(dict(tune_seeds=tune, valid_seeds=valid, tune=rows, validation=v_rows), f, indent=1, default=float)
    print(f"\nsaved {a.out}")
    print("Hand-built worlds: this tunes the thermostat to my assumptions, not to people.")


if __name__ == "__main__":
    main()
