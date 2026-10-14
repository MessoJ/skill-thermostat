"""Checks a list of item dicts before they join the bank.   python -m pilot.validate_items pilot/bank_x.py

Each module under pilot/ named bank_*.py must define ITEMS = [dict(id, pool, d, title, prompt, sig, ref, cases), ...].
"""
import importlib
import json
import re
import sys
import time

from . import runner

NEEDED = ("id", "pool", "d", "title", "prompt", "sig", "ref", "cases")
FORBIDDEN = re.compile(r"\b(import\s+(random|time|os|sys|subprocess|socket|datetime)|input\s*\(|open\s*\(|print\s*\()")


def check_item(it, seen_ids=()):
    errs = []
    for k in NEEDED:
        if k not in it:
            return [f"missing field {k}"]
    if it["id"] in seen_ids:
        errs.append("duplicate id")
    if it["pool"] not in ("A", "B", "C", "P"):
        errs.append("pool must be A, B, C or P")
    if not (-2.0 <= it["d"] <= 2.0):
        errs.append("d outside -2..2")
    if not re.fullmatch(r"[a-z_][a-z0-9_]*\([a-z_0-9, ]*\)", it["sig"]):
        errs.append("bad signature")
    if len(it["cases"]) < 6:
        errs.append("need at least 6 cases")
    if len(it["prompt"]) < 30 or len(it["prompt"]) > 400:
        errs.append("prompt should be 30-400 characters")
    if FORBIDDEN.search(it["ref"]):
        errs.append("reference uses forbidden construct (imports of random/time/os/..., input, open, print)")
    fname, params = it["sig"].split("(", 1)
    params = params.rstrip(")")
    ref = it["ref"].strip("\n") + "\n"
    if not ref.startswith(f"def {fname}({params}):"):
        errs.append("ref must start with the same def line as sig")
        return errs
    try:
        json.dumps([list(c) for c in it["cases"]])
    except TypeError as e:
        errs.append(f"cases not JSON-serializable: {e}")
        return errs
    ns = {}
    try:
        exec(ref, ns)
        runs = []
        for _ in range(2):
            t = time.time()
            runs.append([json.loads(json.dumps(ns[fname](*c))) for c in it["cases"]])
            if time.time() - t > 1.0:
                errs.append("reference takes over 1 second")
        if runs[0] != runs[1]:
            errs.append("reference is not deterministic")
        outs = runs[0]
    except Exception as e:
        return errs + [f"reference raised {type(e).__name__}: {e}"]
    if all(isinstance(o, bool) for o in outs):
        if not (any(outs) and not all(outs)):
            errs.append("yes/no item needs both True and False among the case outputs")
    elif len({json.dumps(o, sort_keys=True) for o in outs}) < 3:
        errs.append("need at least 3 distinct expected outputs")
    if sum(1 for o in outs if o in (None, [], "", 0, {}, False)) > len(outs) // 2:
        errs.append("more than half the expected outputs are empty/zero/None: a stub could pass many cases")
    # a do-nothing stub must fail, and the reference must pass in the real runner
    stub = f"def {fname}({params}):\n    pass\n"
    if runner.run_cases(stub, fname, it["cases"], outs)["ok"]:
        errs.append("starter stub passes all cases")
    r = runner.run_cases(ref, fname, it["cases"], outs)
    if not r["ok"]:
        errs.append(f"reference fails in the runner: {r['fatal'] or r['details']}")
    return errs


def check_module(name):
    mod = importlib.import_module(name)
    items, seen, bad = mod.ITEMS, set(), 0
    for it in items:
        errs = check_item(it, seen)
        seen.add(it.get("id"))
        if errs:
            bad += 1
            print(f"{it.get('id', '?')}: " + "; ".join(errs))
    print(f"{name}: {len(items)} items, {bad} with problems")
    return bad


if __name__ == "__main__":
    sys.exit(1 if sum(check_module(a.replace("/", ".").removesuffix(".py")) for a in sys.argv[1:]) else 0)
