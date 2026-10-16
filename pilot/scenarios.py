"""Scripted learner personas run through the real study engine, to see who gets "keep using AI" and who gets "cut back".

    python -m pilot.scenarios [--seeds 5] [--out scenarios_report.txt]

Each persona has a true skill that rises when the person works unassisted and erodes when AI does the work. The engine decides the helper
level and the verdict exactly as in a real study; only the answers are scripted (the code runner is replaced by the persona's pass/fail
draw). The personas and their rates are my assumptions, so this shows how the decision logic behaves, not how people behave.
"""
import argparse
import os
import tempfile
from collections import Counter

import numpy as np
from scipy.stats import norm

from . import exercises as X
from . import study
from .config import DELTA, STUDY
from .helper import StubHelper
from .study import Engine

ASSIST = {"full": 0.70, "hints": 0.35, "nudge": 0.15, "off": 0.0}     # chance AI turns a miss into a pass (full matches the simulator)
GAIN_SHARE = {"off": 1.0, "nudge": 0.5, "hints": 0.25, "full": 0.0}   # share of the persona's learning rate earned at each helper level

# theta0: true starting skill. gain: skill gained per unassisted task. decay: skill lost per fully assisted task.
PERSONAS = {
    "student: strong, skill holds":        dict(theta0=1.2, gain=0.005, decay=0.0),
    "student: strong but AI-dependent":    dict(theta0=1.0, gain=0.01, decay=0.04),
    "student: weak, learns by doing":      dict(theta0=-0.5, gain=0.03, decay=0.005),
    "student: weak and sliding":           dict(theta0=-0.2, gain=0.005, decay=0.05),
    "student: gets outside help on probes": dict(theta0=-0.3, gain=0.005, decay=0.04, secret_ai=0.6),
    "student: erratic answers":            dict(theta0=0.3, gain=0.01, decay=0.01, flip=0.35),
    "student: quits early":                dict(theta0=1.2, gain=0.005, decay=0.0, max_tasks=STUDY["anchors"] + 4),
    "staff: meets role standard":          dict(theta0=1.0, gain=0.01, decay=0.01, floor_abs=0.4),
    "staff: below role standard":          dict(theta0=0.0, gain=0.03, decay=0.02, floor_abs=0.6),
    "staff: delivery crunch (urgent)":     dict(theta0=0.8, gain=0.01, decay=0.02, urgent=True),
}


def run_persona(P, arm, seed, db):
    eng = Engine(db, helper=StubHelper())
    uid = eng.join(True, floor_abs=P.get("floor_abs"))["user"]
    with eng.tx() as c:
        c.execute("UPDATE users SET arm=?, seed=? WHERE id=?", (arm, int(seed) * 7 + 1, uid))
    rng = np.random.default_rng(seed)
    theta, theta0 = P["theta0"], P["theta0"]
    floor_true = P["floor_abs"] if "floor_abs" in P else theta0 - DELTA
    decision = {"ok": False}

    def fake_run(code, fname, cases, expected, timeout=10):
        ok = decision["ok"]
        n = len(cases)
        return dict(ok=ok, passed=n if ok else 0, total=n, fatal=None,
                    details=[dict(ok=ok, got=None, err=None) for _ in cases[:n]])

    real = study.runner.run_cases
    study.runner.run_cases = fake_run
    below = n_prac = n_assisted = 0
    tiers = Counter()
    try:
        for _ in range(P.get("max_tasks", 10 ** 6)):
            view = eng.next_task(uid, urgent=P.get("urgent", False))
            if view.get("done"):
                break
            with eng.tx() as c:
                ex = X.BANK[c.execute("SELECT ex_id FROM tasks WHERE id=?", (view["task_id"],)).fetchone()[0]]
            tier, kind = view["tier"], view["kind"]
            p_solo = norm.cdf(1.5 * (theta - ex.d))
            cheats = tier == "off" and kind == "practice" and not view.get("lockdown", False) and rng.random() < P.get("secret_ai", 0)
            if cheats:
                p = p_solo + (1 - p_solo) * ASSIST["full"]
                if rng.random() < 0.7:
                    eng.log_event(uid, view["task_id"], "paste", dict(chars=150))
            else:
                p = p_solo + (1 - p_solo) * ASSIST[tier]
            ok = rng.random() < p
            if rng.random() < P.get("flip", 0):
                ok = bool(rng.random() < 0.5)
            decision["ok"] = bool(ok)
            eng.submit(uid, view["task_id"], "pass")
            share = 0.0 if cheats else GAIN_SHARE[tier]
            theta += P["gain"] * share - (P["decay"] if (tier == "full" or cheats) else 0.0)
            if kind == "practice":
                n_prac += 1
                below += theta < floor_true
                n_assisted += tier != "off"
                tiers[tier] += 1
    finally:
        study.runner.run_cases = real
    s = eng.summary()[0]
    return dict(theta0=theta0, theta_end=float(theta), floor=floor_true, below=below / max(n_prac, 1),
                ai_share=n_assisted / max(n_prac, 1), verdict=s["verdict"], suspect=s["suspect_tasks"],
                c_hat=s["contamination_est"], assess_b=s["assess_b"], assess_c=s["assess_c"], tiers=dict(tiers))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--out", default="scenarios_report.txt")
    a = ap.parse_args(argv)
    lines = [f"Each row: {a.seeds} simulated runs of that persona. 'AI share' = practice tasks that got any AI help; 'below floor' = share of practice",
             "time the persona's TRUE skill was under its floor; 'end skill' = true skill at the end. Verdict = what the system would tell a",
             "teacher or manager (counts across runs). Thermostat arm vs always-on arm shows what the thermostat changes.", ""]
    hdr = f"{'persona':38}{'arm':12}{'AI share':>9}{'below floor':>12}{'end skill':>10}   verdicts"
    lines += [hdr, "-" * len(hdr)]
    for name, P in PERSONAS.items():
        for arm in ("thermostat", "always_on"):
            runs = []
            for sd in range(a.seeds):
                with tempfile.TemporaryDirectory() as d:
                    runs.append(run_persona(P, arm, sd, os.path.join(d, "s.db")))
            vs = Counter((r["verdict"] or {}).get("status", "no verdict yet") for r in runs)
            lines.append(f"{name if arm == 'thermostat' else '':38}{arm:12}{np.mean([r['ai_share'] for r in runs]):9.0%}"
                         f"{np.mean([r['below'] for r in runs]):12.0%}{np.mean([r['theta_end'] for r in runs]):+10.2f}   "
                         + ", ".join(f"{k} x{v}" for k, v in vs.most_common()))
        lines.append("")
    text = "\n".join(lines)
    open(a.out, "w").write(text)
    print(text)


if __name__ == "__main__":
    main()
