import threading

import pytest

from pilot import exercises as X
from pilot import runner, runner_service


@pytest.fixture
def service(monkeypatch):
    srv = runner_service.make_server("127.0.0.1", 0)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    monkeypatch.setenv("RUNNER_URL", f"http://127.0.0.1:{srv.server_address[1]}")
    yield srv
    srv.shutdown()


def test_remote_backend_matches_local(service):
    for e in X.pool("P")[:5]:
        remote = runner.run_cases(e.ref, e.fname, e.cases, e.expected())
        assert remote["ok"] and remote["passed"] == len(e.cases)
        assert not runner.run_cases(e.starter, e.fname, e.cases, e.expected())["ok"]


def test_remote_handles_loops_and_errors(service):
    e = X.pool("P")[0]
    r = runner.run_cases("def %s(*a):\n    while True: pass\n" % e.fname, e.fname, e.cases, e.expected())
    assert not r["ok"] and r["fatal"] and ("Stopped" in r["fatal"] or "Timed out" in r["fatal"])
    assert runner.run_cases("def %s(:\n" % e.fname, e.fname, e.cases, e.expected())["fatal"]


def test_key_is_enforced(service, monkeypatch):
    monkeypatch.setenv("RUNNER_KEY", "s3cret")
    e = X.pool("P")[0]
    r = runner.run_cases(e.ref, e.fname, e.cases, e.expected())          # client sends the key, server env has it too
    assert r["ok"]
    monkeypatch.setenv("RUNNER_KEY", "wrong")                            # server reads env at request time, client now differs
    # same process shares env, so emulate a mismatch by calling the service without the header
    import json, urllib.request, urllib.error
    monkeypatch.setenv("RUNNER_KEY", "s3cret")
    req = urllib.request.Request(__import__("os").environ["RUNNER_URL"] + "/run", json.dumps({}).encode(), {"Content-Type": "application/json"})
    with pytest.raises(urllib.error.HTTPError) as err:
        urllib.request.urlopen(req)
    assert err.value.code == 403


def test_bad_jobs_rejected_and_unreachable_runner_fails_closed(service, monkeypatch):
    import json, urllib.request, urllib.error
    url = __import__("os").environ["RUNNER_URL"]
    for bad in ({"code": 1}, {"code": "x", "fname": "not valid", "cases": [], "expected": []}):
        req = urllib.request.Request(url + "/run", json.dumps(bad).encode(), {"Content-Type": "application/json"})
        with pytest.raises(urllib.error.HTTPError) as err:
            urllib.request.urlopen(req)
        assert err.value.code == 400
    monkeypatch.setenv("RUNNER_URL", "http://127.0.0.1:1")               # nothing listens there
    e = X.pool("P")[0]
    r = runner.run_cases(e.ref, e.fname, e.cases, e.expected())
    assert not r["ok"] and "unavailable" in r["fatal"]
