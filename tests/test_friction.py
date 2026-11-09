"""Unit tests for Step 3: Continuous Friction & Fault-Injection Engine (skill_thermostat/friction.py)."""
from __future__ import annotations

import ast
from pathlib import Path

from skill_thermostat import friction
from skill_thermostat.friction import (
    LEVEL_FULL,
    LEVEL_PROBE_FAULT,
    LEVEL_SKELETON,
    apply,
    apply_with_metadata,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
FILTERS_SRC = (REPO_ROOT / "skill_thermostat" / "filters.py").read_text(encoding="utf-8")
CONTROLLER_SRC = (REPO_ROOT / "skill_thermostat" / "controller.py").read_text(encoding="utf-8")


def test_level_full_preserves_code_untouched():
    out = apply(FILTERS_SRC, mode=LEVEL_FULL)
    assert out == FILTERS_SRC
    ast.parse(out)
    assert friction.LAST_METADATA["mode"] == LEVEL_FULL
    assert friction.LAST_METADATA["mutated"] is False


def test_level_skeleton_strips_bodies_and_preserves_docstrings_and_syntax():
    for src in (FILTERS_SRC, CONTROLLER_SRC):
        res = apply_with_metadata(src, mode=LEVEL_SKELETON)
        tree = ast.parse(res.code)
        assert 'raise NotImplementedError("complete unassisted")' in res.code or "raise NotImplementedError('complete unassisted')" in res.code
        assert res.metadata["mutated"] is True
        assert res.metadata["count"] >= 2

        # Verify every function/method body ends with raise NotImplementedError("complete unassisted")
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert len(node.body) in (1, 2)
                last_stmt = node.body[-1]
                assert isinstance(last_stmt, ast.Raise)


def test_level_probe_fault_injects_deterministic_boundary_mutation_with_line_metadata():
    res1 = apply_with_metadata(FILTERS_SRC, mode=LEVEL_PROBE_FAULT, seed=0)
    res2 = apply_with_metadata(FILTERS_SRC, mode=LEVEL_PROBE_FAULT, seed=0)
    assert res1.code == res2.code
    assert res1.code != FILTERS_SRC

    # Valid Python syntax must be preserved
    ast.parse(res1.code)

    meta = res1.metadata
    assert meta["mode"] == LEVEL_PROBE_FAULT
    assert meta["mutated"] is True
    assert isinstance(meta["lineno"], int) and meta["lineno"] >= 1
    assert meta["original_op"] != meta["mutated_op"]
    assert meta["original_snippet"] != meta["mutated_snippet"]
    assert meta["mutated_snippet"] in res1.code


def test_controller_skeleton_and_probe_fault_transformations():
    skel = apply(CONTROLLER_SRC, mode=LEVEL_SKELETON)
    ast.parse(skel)
    assert "NotImplementedError" in skel

    fault_res = apply_with_metadata(CONTROLLER_SRC, mode=LEVEL_PROBE_FAULT, seed=0)
    ast.parse(fault_res.code)
    assert fault_res.metadata["mutated"] is True
    assert fault_res.metadata["lineno"] > 0
