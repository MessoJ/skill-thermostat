"""Per-arm summary of a study database.   python -m pilot.report study.db"""
import sys
from collections import defaultdict

from .study import Engine


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def _fmt(x):
    return "  -  " if x is None else f"{x:5.2f}"


def report(db):
    rows = Engine(db).summary()
    by = defaultdict(list)
    for r in rows:
        by[r["arm"]].append(r)
    lines = [f"{'arm':14}{'n':>3} {'anchor':>6} {'practice':>8} {'probes':>6} {'mid(B)':>6} {'post(C)':>7} {'suspect':>7}"]
    for arm, rs in sorted(by.items()):
        lines.append(f"{arm:14}{len(rs):>3} {_fmt(_mean(r['anchors'] for r in rs)):>6} "
                     f"{_fmt(_mean(r['practice'] for r in rs)):>8} {_fmt(_mean(r['probes'] for r in rs)):>6} "
                     f"{_fmt(_mean(r['assess_b'] for r in rs)):>6} {_fmt(_mean(r['assess_c'] for r in rs)):>7} "
                     f"{sum(r['suspect_tasks'] for r in rs):>7}")
    lines.append("")
    lines.append("Pass rates (0-1). The outcome of interest is post(C) minus anchor on unassisted items, per arm.")
    lines.append("With a few dozen participants and nominal item difficulties this is a feasibility check, not a result.")
    return "\n".join(lines)


if __name__ == "__main__":
    print(report(sys.argv[1] if len(sys.argv) > 1 else "study.db"))
