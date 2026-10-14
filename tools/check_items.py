"""Validate a batch of exercise items.    python tools/check_items.py pilot/bank_ext/items_x.py [--existing]

Checks per item: id/pool format and uniqueness (also against the existing bank), normalized title and AST
collision checks across pools, difficulty range, JSON-safe arguments, reference passes every case, an empty
`pass` starter fails, enough distinct expected outputs, 5+ cases, runtime, and allowed stdlib imports.
"""
import ast
import importlib.util
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pilot import exercises as X  # noqa: E402
from pilot import runner  # noqa: E402

ALLOWED_IMPORTS = {"math", "re", "itertools", "collections", "functools", "heapq", "bisect", "string", "operator"}


def _norm_title(title):
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def _ast_fingerprint(ref):
    try:
        tree = ast.parse(ref.strip())
    except SyntaxError:
        return None
    return tuple(
        type(n).__name__
        for n in ast.walk(tree)
        if not isinstance(n, (ast.Load, ast.Store, ast.Name, ast.arg, ast.Module))
    )


def load(path):
    spec = importlib.util.spec_from_file_location("batch", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.ITEMS


def check(path, allow_existing=False):
    problems = []
    existing_by_id = {e.id: e for e in X.ALL}
    items = load(path)
    batch_ids = set()
    batch_titles = {}

    for t in items:
        if len(t) != 8:
            problems.append(f"{t[0] if t else '?'}: tuple must have 8 fields")
            continue
        id_, pool, d, title, prompt, sig, ref, cases = t
        tag = id_
        if not re.fullmatch(r"[abcp]\d{2,3}", id_) or id_[0].upper() != pool.upper():
            problems.append(f"{tag}: id must be pool letter + digits matching pool {pool!r}")
        if id_ in batch_ids:
            problems.append(f"{tag}: duplicate id inside batch")
        batch_ids.add(id_)

        nt = _norm_title(title)
        if nt in batch_titles and {pool, batch_titles[nt][1]} != {"B", "C"}:
            problems.append(f"{tag}: duplicate title {title!r} with {batch_titles[nt][0]} inside batch")
        batch_titles[nt] = (id_, pool)

        if id_ in existing_by_id and not allow_existing:
            if sum(1 for e in X.ALL if e.id == id_) > 1 or id_ not in {x[0] for x in items}:
                problems.append(f"{tag}: id already used in the bank")

        # Cross-pool duplicate check: practice items (P) must not duplicate assessment/anchor items (A/B/C)
        fp = _ast_fingerprint(ref)
        fname = sig.split("(", 1)[0].strip()
        for other in X.ALL:
            if other.id == id_:
                continue
            if (pool == "P") != (other.pool == "P"):
                if fname == other.fname and fp and fp == _ast_fingerprint(other.ref):
                    problems.append(f"{tag}: identical function name and AST to {other.id} (pool {other.pool})")

        if pool not in "ABCP":
            problems.append(f"{tag}: bad pool {pool!r}")
        if not -2.0 <= d <= 2.0:
            problems.append(f"{tag}: difficulty {d} outside [-2, 2]")
        if len(prompt) < 25:
            problems.append(f"{tag}: prompt too short")
        if len(cases) < 5:
            problems.append(f"{tag}: needs 5+ cases")
        for imp in re.findall(r"^\s*(?:from|import)\s+([a-zA-Z_]+)", ref, re.M):
            if imp not in ALLOWED_IMPORTS:
                problems.append(f"{tag}: import {imp} not allowed")
        try:
            json.dumps([list(c) for c in cases])
        except TypeError as e:
            problems.append(f"{tag}: cases not JSON-safe ({e})")
            continue
        ex = X._ex(*t)
        t0 = time.time()
        r = runner.run_cases(ex.ref, ex.fname, ex.cases, ex.expected())
        dt = time.time() - t0
        if not r["ok"]:
            problems.append(f"{tag}: reference fails its own cases: {r['fatal'] or r['details']}")
        if dt > 5:
            problems.append(f"{tag}: slow ({dt:.1f}s)")
        vals = ex.expected()
        need = 2 if all(isinstance(v, bool) for v in vals) else 3
        if len({repr(v) for v in vals}) < need:
            problems.append(f"{tag}: expected outputs too uniform ({len({repr(v) for v in vals})} distinct)")
        if all(v is None for v in vals):
            problems.append(f"{tag}: every expected output is None (starter would pass)")
        if runner.run_cases(ex.starter, ex.fname, ex.cases, vals)["ok"]:
            problems.append(f"{tag}: the empty starter passes")
        if len(set(map(repr, ex.cases))) != len(ex.cases):
            problems.append(f"{tag}: duplicate cases")

    by = {}
    for t in items:
        by.setdefault(t[1], []).append(t[2])
    print(f"{path}: {len(items)} items; per pool: " + ", ".join(
        f"{k}={len(v)} (d {min(v):+.1f}..{max(v):+.1f})" for k, v in sorted(by.items())
    ))
    for p in problems:
        print("  PROBLEM", p)
    return not problems


if __name__ == "__main__":
    allow_ex = "--existing" in sys.argv
    paths = [p for p in sys.argv[1:] if not p.startswith("--")]
    ok = all(check(p, allow_existing=allow_ex) for p in paths)
    sys.exit(0 if ok else 1)
