"""Extra exercises, one module per author batch (items_*.py), each defining ITEMS = [(id, pool, d, title, prompt, sig, ref, cases), ...]
in the same argument order as pilot.exercises._ex."""
import importlib
import pkgutil

# Practice items dropped because they repeat a baseline (A) or assessment (B/C) item, or each other. Practice must not
# train the exact problems that are later used to measure.
DROPPED = {"p21", "p44", "p54", "p68", "p73", "p74", "p77", "p81", "p90"}
ITEMS = []
for _m in sorted(m.name for m in pkgutil.iter_modules(__path__) if m.name.startswith("items_")):
    ITEMS.extend(t for t in importlib.import_module(f"{__name__}.{_m}").ITEMS if t[0] not in DROPPED)
