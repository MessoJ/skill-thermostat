import numpy as np

from skill_thermostat import SkillFilter, Summary, Thermostat, ThermostatConfig
from skill_thermostat import sim
from skill_thermostat.model import GRID, p_assisted, p_solo

C_GRID = (0.0, 0.1, 0.2, 0.3, 0.4)


def run_worker(theta, c, n_anchor=30, n_probe=300, seed=0):
    """One worker: trusted anchors, then ordinary probes that are secretly assisted with prob c."""
    rng = np.random.default_rng(seed)
    F = SkillFilter(1, GRID, c_grid=C_GRID)
    yes, no = np.ones(1, bool), np.zeros(1, bool)
    for _ in range(n_anchor):
        d = rng.normal(0, 0.8, 1)
        F.update(d, rng.random(1) < p_solo(theta, d), yes, trusted=yes)
    for _ in range(n_probe):
        d = rng.normal(0, 0.8, 1)
        p = p_solo(theta, d)
        if rng.random() < c:
            p = p_assisted(p)
        F.update(d, rng.random(1) < p, yes, trusted=no)
    return F, F.summary()


def test_filter_concentrates_on_true_skill():
    _, s = run_worker(theta=0.5, c=0.0)
    assert abs(s.mean[0] - 0.5) < 0.15
    assert s.sd[0] < 0.15


def test_posterior_stays_normalized():
    F, _ = run_worker(theta=0.2, c=0.2, n_probe=50)
    F.predict()
    F.predict(wide=np.ones(1, bool))
    assert np.allclose(F.post.sum((1, 2)), 1.0)


def test_contamination_is_detected_on_average():
    # Per-worker estimates are noisy (sd ~0.07 at 300 probes), so test the mean over seeds.
    clean = np.mean([run_worker(0.5, 0.0, seed=s)[1].c_mean[0] for s in range(10)])
    dirty = np.mean([run_worker(0.5, 0.3, seed=s)[1].c_mean[0] for s in range(10)])
    assert dirty > clean + 0.10


def test_controller_assistance_rises_with_margin():
    n = 5
    q10 = np.linspace(-0.6, 0.6, n)
    cdf = np.cumsum(np.full((n, len(GRID)), 1.0 / len(GRID)), 1)
    summ = Summary(q10 + 0.2, np.full(n, 0.1), q10, cdf, np.zeros(n))
    ctl = Thermostat(ThermostatConfig(), GRID)
    alpha, _, _ = ctl.decide(summ, np.zeros(n), np.ones(n, bool), np.ones(n), np.ones(n))
    assert np.all(np.diff(alpha) >= 0) and alpha.min() >= 0 and alpha.max() <= 1


def test_high_stakes_tasks_are_never_withheld_or_probed():
    n = 50
    cdf = np.cumsum(np.full((n, len(GRID)), 1.0 / len(GRID)), 1)
    summ = Summary(np.full(n, -3.0), np.full(n, 1.0), np.full(n, -3.0), cdf, np.zeros(n))
    ctl = Thermostat(ThermostatConfig(sentinel_rate=1.0), GRID)
    alpha, off, sent = ctl.decide(summ, np.zeros(n), np.zeros(n, bool), np.zeros(n), np.zeros(n))
    assert np.all(alpha == 1.0) and not off.any() and not sent.any()


def test_simulation_is_deterministic():
    w = sim.WORLDS[1]
    a = sim.simulate(w, "thermostat_robust", seed=1, N=40, T=60)
    b = sim.simulate(w, "thermostat_robust", seed=1, N=40, T=60)
    assert a == b or all(
        (np.isnan(a[k]) and np.isnan(b[k])) or a[k] == b[k] for k in a
    )
