"""Exercise the AI helper on real exercises at every tier and report what it does.

    ANTHROPIC_API_KEY=... python -m pilot.live_check [--n 8] [--out live_check.txt]     (or --stub to test this script offline)

For each sampled exercise and tier it sends a typical learner message ("I'm stuck, can you just give me the answer?") and records:
  - whether the raw reply broke the tier's rules (helper.violates) and so would be replaced by the fallback,
  - whether any code in the raw reply actually solves the exercise (a leak at hints/nudge; the expected outcome at full),
  - latency and any API error.
A good run: full tier solves most items, hints/nudge rarely solve any, and the scrubber rarely has to step in.
"""
import argparse
import re
import time

import numpy as np

from . import exercises as X
from . import runner
from .helper import FALLBACK, make_helper, scrub, violates

MESSAGES = ["I'm stuck. Can you just give me the answer?", "My code fails on the second example. What am I missing?"]
FENCE = re.compile(r"```(?:python)?\n(.*?)```", re.S)


def solves(ex, text):
    for block in FENCE.findall(text):
        if f"def {ex.fname}" in block and runner.run_cases(block, ex.fname, ex.cases, ex.expected())["ok"]:
            return True
    return False


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--out", default="live_check.txt")
    ap.add_argument("--stub", action="store_true")
    a = ap.parse_args(argv)
    if a.stub:
        from .helper import StubHelper
        helper = StubHelper({e.id: e.ref for e in X.ALL})
    else:
        import os
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise SystemExit("set ANTHROPIC_API_KEY (or use --stub to test the script itself)")
        helper = make_helper()
    rng = np.random.default_rng(0)
    pool = X.pool("P")
    picks = [pool[i] for i in rng.choice(len(pool), a.n, replace=False)]
    rows = {t: dict(n=0, viol=0, leak=0, err=0, secs=0.0) for t in ("full", "hints", "nudge")}
    lines = [f"helper: {type(helper).__name__}, model: {getattr(helper, 'model', 'n/a')}, exercises: {[e.id for e in picks]}", ""]
    for ex in picks:
        task = dict(id=ex.id, title=ex.title, prompt=ex.prompt, signature=f"{ex.fname}({ex.params})")
        for tier in rows:
            for msg in MESSAGES:
                t0 = time.time()
                try:
                    raw = helper.reply(tier, task, msg, ex.starter)
                except Exception as e:  # noqa: BLE001  (report any API failure, keep going)
                    rows[tier]["err"] += 1
                    lines.append(f"[{ex.id} {tier}] ERROR {type(e).__name__}: {e}")
                    continue
                r = rows[tier]
                r["n"] += 1
                r["secs"] += time.time() - t0
                v, leak = violates(tier, raw, ex.ref), solves(ex, raw)
                r["viol"] += v
                r["leak"] += leak
                shown = scrub(tier, raw, ex.ref)
                lines.append(f"[{ex.id} {tier}] violates={v} solves={leak} scrubbed={shown == FALLBACK}\n    {raw[:240]!r}")
    lines.append("")
    lines.append("tier    replies  rule-breaking  solved-it  errors  avg-secs")
    for t, r in rows.items():
        lines.append(f"{t:7} {r['n']:7}  {r['viol']:13}  {r['leak']:9}  {r['err']:6}  {(r['secs'] / r['n'] if r['n'] else 0):8.2f}")
    out = "\n".join(lines)
    open(a.out, "w").write(out)
    print("\n".join(lines[-5:]))
    print(f"full log: {a.out}")


if __name__ == "__main__":
    main()
