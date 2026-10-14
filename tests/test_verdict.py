import os
import tempfile
from collections import Counter

import numpy as np

from pilot import verdict as V
from pilot.config import CONTROLLER
from pilot.scenarios import PERSONAS, run_persona

BASE = dict(mean=1.0, sd=0.25, floor=0.0, n_meas=30, trend=0.0, n_probes=10, since_last=3)


def d(lower, **kw):
    a = dict(BASE, lower=lower)
    a.update(kw)
    mean, sd, floor, n, trend = a.pop("mean"), a.pop("sd"), a.pop("floor"), a.pop("n_meas"), a.pop("trend")
    return V.decide(mean, sd, a.pop("lower"), floor, n, trend, **a).status


def test_margin_bands_follow_the_controller_thresholds():
    assert d(CONTROLLER.m_hi + 0.05) == "keep_using_ai"
    assert d((CONTROLLER.m_lo + CONTROLLER.m_hi) / 2) == "use_ai_in_moderation"
    assert d(CONTROLLER.m_lo - 0.1) == "reduce_ai"
    assert d(-0.2, mean=-0.1) == "practice_without_ai"
    assert d(0.5, trend=-0.3) == "keep_but_watch"


def test_evidence_and_integrity_checks_come_first():
    assert d(0.5, n_meas=5) == "not_enough_evidence"
    assert d(0.5, sd=0.6) == "not_enough_evidence"
    assert d(0.5, n_probes=1) == "not_enough_evidence"                       # baseline-relative floor needs post-baseline checks
    assert d(0.5, n_probes=0, relative_floor=False) == "keep_using_ai"        # an absolute standard is informative from the baseline
    assert d(0.5, since_last=20) == "stale_evidence"
    assert d(0.5, probe_suspect=0.5, n_probe_obs=6) == "check_measurements"
    assert d(0.5, probe_suspect=0.5, n_probe_obs=2) == "keep_using_ai"        # too few observations to judge activity
    assert d(0.5, anchor_suspect=0.3) == "check_measurements"


def _runs(name, arm, n=4):
    out = []
    for sd in range(n):
        with tempfile.TemporaryDirectory() as t:
            out.append(run_persona(PERSONAS[name], arm, sd, os.path.join(t, "s.db")))
    return out


def test_declining_student_is_protected_by_the_thermostat():
    th, ao = _runs("student: strong but AI-dependent", "thermostat"), _runs("student: strong but AI-dependent", "always_on")
    assert np.mean([r["theta_end"] for r in th]) > np.mean([r["theta_end"] for r in ao]) + 0.3
    assert np.mean([r["below"] for r in th]) < np.mean([r["below"] for r in ao])


def test_always_on_users_are_never_certified_as_safe():
    for name in ("student: strong, skill holds", "staff: meets role standard"):
        for r in _runs(name, "always_on", 3):
            assert r["verdict"]["status"] in ("not_enough_evidence", "stale_evidence"), r["verdict"]["status"]


def test_outside_help_with_paste_activity_is_flagged_not_certified():
    st = Counter(r["verdict"]["status"] for r in _runs("student: gets outside help on probes", "thermostat"))
    assert st["check_measurements"] >= 3 and "keep_using_ai" not in st


def test_honest_fast_learners_are_not_flagged():
    for name in ("staff: below role standard", "student: weak, learns by doing"):
        assert all(r["verdict"]["status"] != "check_measurements" for r in _runs(name, "thermostat")), name


def test_staff_below_standard_gets_no_ai_until_they_reach_it_and_early_quitters_get_no_verdict():
    for r in _runs("staff: below role standard", "thermostat", 3):
        assert r["ai_share"] < 0.2 and r["verdict"]["status"] in ("reduce_ai", "practice_without_ai")
    st = Counter(r["verdict"]["status"] for r in _runs("student: quits early", "thermostat"))
    assert st["not_enough_evidence"] >= 3


def test_urgent_work_keeps_getting_full_help():
    for r in _runs("staff: delivery crunch (urgent)", "thermostat", 3):
        assert r["tiers"].get("full", 0) >= 3
