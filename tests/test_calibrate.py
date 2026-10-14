import numpy as np
from scipy.stats import norm

from pilot.calibrate import calibrate
from skill_thermostat.model import A_DISC


def _simulate(n_people, n_items, per_person, seed, spread=1.0):
    rng = np.random.default_rng(seed)
    d_true = rng.uniform(-1.4, 1.4, n_items)
    theta = rng.normal(0, 1, n_people)
    resp = []
    for p in range(n_people):
        for j in rng.choice(n_items, per_person, replace=False):
            resp.append((f"u{p}", f"i{j}", int(rng.random() < norm.cdf(A_DISC * (theta[p] - d_true[j])))))
    return d_true, resp


def test_recovers_difficulties_from_simulated_learners_even_with_bad_nominals():
    d_true, resp = _simulate(600, 60, 30, seed=1)
    rng = np.random.default_rng(2)
    nominal = {f"i{j}": float(d_true[j] + rng.normal(0, 0.5)) for j in range(60)}   # guesses off by ~0.5
    res = calibrate(resp, nominal, prior_sd=1.0)
    est = np.array([res[f"i{j}"]["d"] for j in range(60)])
    nom = np.array([nominal[f"i{j}"] for j in range(60)])
    rmse_cal, rmse_nom = np.sqrt(np.mean((est - d_true) ** 2)), np.sqrt(np.mean((nom - d_true) ** 2))
    assert np.corrcoef(est, d_true)[0, 1] > 0.97
    assert rmse_cal < 0.6 * rmse_nom, (rmse_cal, rmse_nom)
    assert all(v["n"] >= 200 and v["se"] is not None and v["se"] < 0.3 for v in res.values())


def test_thin_data_stays_near_nominal():
    d_true, resp = _simulate(20, 60, 5, seed=3)
    nominal = {f"i{j}": 0.5 for j in range(60)}
    res = calibrate(resp, nominal, prior_sd=0.3)
    assert max(abs(v["d"] - 0.5) for v in res.values()) < 0.7


def test_cli_reads_database_and_writes_json(tmp_path, monkeypatch):
    import json
    import sqlite3

    from pilot import calibrate as cal
    from pilot import exercises as X
    from pilot.study import Engine

    db = str(tmp_path / "s.db")
    Engine(db)
    rng = np.random.default_rng(0)
    ids = [e.id for e in X.pool("P")][:20]
    con = sqlite3.connect(db)
    for p in range(120):
        th = rng.normal()
        for i in rng.choice(ids, 12, replace=False):
            ok = int(rng.random() < norm.cdf(A_DISC * (th - X.BANK[i].d)))
            con.execute("INSERT INTO tasks(user, ex_id, kind, tier, off, suspect, done, passed) VALUES (?,?,?,?,?,?,?,?)",
                        (f"u{p}", i, "practice", "off", 1, 0, 1.0, ok))
    con.execute("INSERT INTO tasks(user, ex_id, kind, tier, off, suspect, done, passed) VALUES ('x','p01','practice','off',1,1,1.0,1)")
    con.commit(); con.close()
    out = tmp_path / "cal.json"
    cal.main([db, "--out", str(out)])
    j = json.load(open(out))
    assert len(j["items"]) == 20 and all(abs(v - X.BANK[k].d) < 1.0 for k, v in j["items"].items())
    assert sum(v["n"] for v in j["detail"].values()) == 120 * 12     # the suspect row was excluded
