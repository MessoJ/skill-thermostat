import threading

import pytest

from pilot import exercises as X
from pilot import runner
from pilot.config import STUDY
from pilot.helper import FALLBACK, StubHelper, scrub, violates
from pilot.study_app import create_app

SOL = {e.id: e.ref for e in X.ALL}
WRONG = "def nothing(*a):\n    return None\n"


# ------------------------------------------------------------------ item bank
def test_bank_references_pass_and_starters_fail():
    for e in X.ALL:
        r = runner.run_cases(e.ref, e.fname, e.cases, e.expected())
        assert r["ok"], (e.id, r)
        assert not runner.run_cases(e.starter, e.fname, e.cases, e.expected())["ok"], e.id


def test_bank_has_varied_expected_outputs_and_matched_pools():
    for e in X.ALL:
        vals = e.expected()
        need = 2 if all(isinstance(v, bool) for v in vals) else 3   # a yes/no function can only return two values
        assert len({repr(v) for v in vals}) >= need, e.id
        assert len(vals) >= 4, e.id
    assert len(X.pool("B")) == len(X.pool("C")) == 12
    assert len(X.ALL) >= 150
    assert len({e.id for e in X.ALL}) == len(X.ALL)


# ------------------------------------------------------------------ runner
def test_runner_failure_modes():
    e = X.pool("P")[0]
    assert runner.run_cases("def %s(:\n" % e.fname, e.fname, e.cases, e.expected())["fatal"]
    loop = "def %s(*a):\n    while True: pass\n" % e.fname
    r = runner.run_cases(loop, e.fname, e.cases, e.expected())
    assert not r["ok"]
    noisy = "print('hi')\n" + e.ref
    assert runner.run_cases(noisy, e.fname, e.cases, e.expected())["ok"]


# ------------------------------------------------------------------ helper policy
def test_helper_scrub_limits():
    big = "```python\n" + "\n".join(f"x{i}=1" for i in range(6)) + "\n```"
    assert violates("hints", big) and scrub("hints", big) == FALLBACK
    assert not violates("full", big)
    assert violates("nudge", "try:\n```\nx=1\n```")
    ref = "def f(a):\n    s = 0\n    for v in a:\n        s += v\n    return s\n"
    assert violates("hints", "for v in a:\n s += v\n return s\n s = 0", ref)
    assert not violates("hints", "Think about an accumulator.", ref)


# ------------------------------------------------------------------ app flow
@pytest.fixture
def client(tmp_path):
    app = create_app(str(tmp_path / "s.db"), StubHelper(SOL))
    return app.test_client(), app.engine


def join(c):
    r = c.post("/api/join", json={"consent": True})
    assert r.status_code == 200
    return r.json


def hdr(u):
    return {"X-User": u["user"]}


def solve_current(c, eng, u, ok=True):
    t = c.post("/api/next", json={}, headers=hdr(u)).json
    if t.get("done"):
        return t
    with eng.tx() as con:
        ex_id = con.execute("SELECT ex_id FROM tasks WHERE id=?", (t["task_id"],)).fetchone()[0]
    code = SOL[ex_id] if ok else WRONG
    r = c.post("/api/submit", json={"task_id": t["task_id"], "code": code}, headers=hdr(u))
    assert r.status_code == 200, r.json
    return dict(t, ex_id=ex_id, passed=r.json["passed"])


def test_consent_required_and_arm_balance(client):
    c, eng = client
    assert c.post("/api/join", json={}).status_code == 400
    arms = [join(c)["arm"] for _ in range(9)]
    assert {a: arms.count(a) for a in set(arms)} == {"thermostat": 3, "always_on": 3, "fixed_drills": 3}


def test_unknown_user_and_missing_user(client):
    c, _ = client
    assert c.post("/api/next", json={}, headers={"X-User": "nope"}).status_code == 404
    assert c.post("/api/next", json={}).status_code == 400


def test_anchors_first_locked_and_pending_task_is_stable(client):
    c, eng = client
    u = join(c)
    t1 = c.post("/api/next", json={}, headers=hdr(u)).json
    t2 = c.post("/api/next", json={}, headers=hdr(u)).json
    assert t1["task_id"] == t2["task_id"]
    assert t1["kind"] == "anchor" and t1["tier"] == "off" and t1["focus"] and not t1["helper"]
    assert "ref" not in t1 and "cases" not in t1
    r = c.post("/api/helper", json={"task_id": t1["task_id"], "message": "help"}, headers=hdr(u))
    assert r.status_code == 403


def test_full_run_every_arm_invariants(client):
    c, eng = client
    users = [join(c) for _ in range(3)]
    for u in users:
        for _ in range(STUDY["anchors"] + STUDY["practice_total"] + 2 * STUDY["assess_n"] + 3):
            if solve_current(c, eng, u, ok=True).get("done"):
                break
        assert c.get("/api/status", headers=hdr(u)).json["next"] == "done"
    with eng.tx() as con:
        for u in users:
            rows = con.execute("SELECT * FROM tasks WHERE user=? ORDER BY id", (u["user"],)).fetchall()
            ids = [r["ex_id"] for r in rows]
            assert len(ids) == len(set(ids)), "an item repeated"
            assert all(r["done"] for r in rows)
            kinds = [r["kind"] for r in rows]
            assert kinds[:STUDY["anchors"]] == ["anchor"] * STUDY["anchors"]
            assert kinds.count("assess_b") == STUDY["assess_n"] and kinds.count("assess_c") == STUDY["assess_n"]
            assert kinds.count("practice") == STUDY["practice_total"]
            assert kinds[-STUDY["assess_n"]:] == ["assess_c"] * STUDY["assess_n"]
            for r in rows:
                if r["kind"] != "practice":
                    assert r["off"] == 1 and r["alpha"] == 0 and r["lockdown"] == 1
            arm = con.execute("SELECT arm FROM users WHERE id=?", (u["user"],)).fetchone()[0]
            if arm == "always_on":
                assert all(r["off"] == 0 for r in rows if r["kind"] == "practice")
            if arm == "fixed_drills":
                offs = [r["off"] for r in rows if r["kind"] == "practice"]
                assert sum(offs) == len(offs) // STUDY["drill_every"]
    summ = eng.summary()
    assert len(summ) == 3 and all(s["anchors"] == 1.0 for s in summ)


def test_assessments_do_not_update_filter_but_anchors_do(client):
    c, eng = client
    u = join(c)

    def post():
        with eng.tx() as con:
            return con.execute("SELECT post FROM users WHERE id=?", (u["user"],)).fetchone()[0]

    p0 = post()
    solve_current(c, eng, u)
    assert post() != p0                       # an anchor updates the filter
    for _ in range(80):                       # run until the first assessment is pending
        t = c.post("/api/next", json={}, headers=hdr(u)).json
        if t["kind"] == "assess_b":
            break
        solve_current(c, eng, u)
    assert t["kind"] == "assess_b" and t["tier"] == "off"
    p1 = post()
    c.post("/api/submit", json={"task_id": t["task_id"], "code": WRONG}, headers=hdr(u))
    assert post() == p1                       # an assessment does not


def test_urgent_quota_and_never_probed(client):
    c, eng = client
    u = join(c)
    for _ in range(STUDY["anchors"]):
        solve_current(c, eng, u)
    n_urgent = 0
    for _ in range(8):
        t = c.post("/api/next", json={"urgent": True}, headers=hdr(u)).json
        if t["kind"] != "practice":
            solve_current(c, eng, u)
            continue
        n_urgent += t["urgent"]
        if t["urgent"]:
            assert t["tier"] == "full" and not t["focus"]
        solve_current(c, eng, u)
    assert 1 <= n_urgent <= 3


def test_suspicious_events_downgrade_trust_and_are_recorded(client):
    c, eng = client
    u = join(c)
    t = c.post("/api/next", json={}, headers=hdr(u)).json
    with eng.tx() as con:
        assert con.execute("SELECT trusted FROM tasks WHERE id=?", (t["task_id"],)).fetchone()[0] == 1
    r = c.post("/api/event", json={"task_id": t["task_id"], "kind": "paste", "data": {"chars": 200}}, headers=hdr(u))
    assert r.status_code == 200
    assert c.post("/api/event", json={"task_id": t["task_id"], "kind": "bogus"}, headers=hdr(u)).status_code == 400
    with eng.tx() as con:
        ex_id = con.execute("SELECT ex_id FROM tasks WHERE id=?", (t["task_id"],)).fetchone()[0]
    c.post("/api/submit", json={"task_id": t["task_id"], "code": SOL[ex_id]}, headers=hdr(u))
    with eng.tx() as con:
        row = con.execute("SELECT trusted, suspect FROM tasks WHERE id=?", (t["task_id"],)).fetchone()
    assert row["suspect"] == 1 and row["trusted"] == 0


def test_submit_once_only_and_events_on_closed_task_rejected(client):
    c, eng = client
    u = join(c)
    t = c.post("/api/next", json={}, headers=hdr(u)).json
    ok = c.post("/api/submit", json={"task_id": t["task_id"], "code": WRONG}, headers=hdr(u))
    assert ok.status_code == 200 and ok.json["passed"] is False
    assert c.post("/api/submit", json={"task_id": t["task_id"], "code": WRONG}, headers=hdr(u)).status_code == 404
    assert c.post("/api/event", json={"task_id": t["task_id"], "kind": "blur"}, headers=hdr(u)).status_code == 404


def test_concurrent_submits_count_once(client):
    c, eng = client
    u = join(c)
    t = c.post("/api/next", json={}, headers=hdr(u)).json
    codes = []

    def go():
        codes.append(app_client.post("/api/submit", json={"task_id": t["task_id"], "code": WRONG}, headers=hdr(u)).status_code)

    app_client = c
    th = [threading.Thread(target=go) for _ in range(4)]
    [x.start() for x in th]
    [x.join() for x in th]
    assert codes.count(200) == 1
    assert c.get("/api/status", headers=hdr(u)).json["anchors"] == 1


def test_admin_summary_requires_localhost_or_token(client, monkeypatch):
    c, _ = client
    assert c.get("/api/admin/summary", environ_base={"REMOTE_ADDR": "8.8.8.8"}).status_code == 403
    assert c.get("/api/admin/summary", environ_base={"REMOTE_ADDR": "127.0.0.1"}).status_code == 200
    monkeypatch.setenv("ADMIN_TOKEN", "s3cret")
    assert c.get("/api/admin/summary", environ_base={"REMOTE_ADDR": "127.0.0.1"}).status_code == 403
    assert c.get("/api/admin/summary", headers={"X-Admin": "s3cret"}).status_code == 200


def test_run_examples_never_reveals_hidden_cases(client):
    c, eng = client
    u = join(c)
    t = c.post("/api/next", json={}, headers=hdr(u)).json
    r = c.post("/api/run", json={"task_id": t["task_id"], "code": WRONG}, headers=hdr(u)).json
    assert len(r["results"]) <= 2


def test_strong_baseline_learner_still_gets_help_in_thermostat_arm(client):
    """Regression: a perfect baseline used to put the floor above the lower bound, so help was off for everyone strong."""
    c, eng = client
    u = join(c)
    with eng.tx() as con:
        con.execute("UPDATE users SET arm='thermostat' WHERE id=?", (u["user"],))
    for _ in range(STUDY["anchors"]):
        solve_current(c, eng, u, ok=True)
    tiers = []
    for _ in range(10):
        t = solve_current(c, eng, u, ok=True)
        if t.get("kind") == "practice":
            tiers.append(t["tier"])
    assert tiers and sum(x != "off" for x in tiers) >= len(tiers) // 2, tiers


def test_plan_is_deterministic_matched_and_within_pools():
    from pilot.study import Engine
    p1, p2 = Engine.plan(123), Engine.plan(123)
    assert p1 == p2 and Engine.plan(124) != p1
    assert len(set(p1["anchor"])) == STUDY["anchors"] and all(X.BANK[i].pool == "A" for i in p1["anchor"])
    for b, c in zip(p1["assess_b"], p1["assess_c"]):
        assert X.BANK[b].pool == "B" and X.BANK[c].pool == "C" and b[1:] == c[1:]
        assert abs(X.BANK[b].d - X.BANK[c].d) <= 0.05


def test_bank_pool_difficulty_coverage():
    for pool, lo, hi in (("A", -1.4, 1.3), ("P", -1.2, 1.2)):
        ds = [e.d for e in X.pool(pool)]
        assert min(ds) <= lo and max(ds) >= hi, (pool, min(ds), max(ds))


def test_live_check_script_runs_offline(tmp_path):
    from pilot import live_check
    live_check.main(["--stub", "--n", "3", "--out", str(tmp_path / "o.txt")])
    text = (tmp_path / "o.txt").read_text()
    assert "tier    replies" in text and "full" in text


def test_cat_baseline_adapts_difficulty_to_learner_responses(client):
    """CAT selects harder Pool A items when a learner succeeds and easier items when a learner fails."""
    c, eng = client
    u_hi, u_lo = join(c), join(c)
    for _ in range(8):
        solve_current(c, eng, u_hi, ok=True)
        solve_current(c, eng, u_lo, ok=False)
    with eng.tx() as con:
        hi_ds = [X.BANK[r[0]].d for r in con.execute("SELECT ex_id FROM tasks WHERE user=? ORDER BY id", (u_hi["user"],))]
        lo_ds = [X.BANK[r[0]].d for r in con.execute("SELECT ex_id FROM tasks WHERE user=? ORDER BY id", (u_lo["user"],))]
    assert sum(hi_ds[1:]) / len(hi_ds[1:]) > sum(lo_ds[1:]) / len(lo_ds[1:]) + 0.8


def test_weak_baseline_learner_is_not_locked_out_of_ai_help(client):
    """A learner who fails every baseline item starts above their personal floor and receives AI assistance."""
    c, eng = client
    u = join(c)
    with eng.tx() as con:
        con.execute("UPDATE users SET arm='thermostat' WHERE id=?", (u["user"],))
    for _ in range(STUDY["anchors"]):
        solve_current(c, eng, u, ok=False)
    t = c.post("/api/next", json={}, headers=hdr(u)).json
    assert t["kind"] == "practice"
    with eng.tx() as con:
        row = con.execute("SELECT alpha FROM tasks WHERE id=?", (t["task_id"],)).fetchone()
    assert row["alpha"] > 0.0


def test_helper_denied_event_persists_after_403(client):
    """Regression: raising Forbidden inside tx() previously rolled back the helper_denied event."""
    c, eng = client
    u = join(c)
    t = c.post("/api/next", json={}, headers=hdr(u)).json
    r = c.post("/api/helper", json={"task_id": t["task_id"], "message": "give answer"}, headers=hdr(u))
    assert r.status_code == 403
    with eng.tx() as con:
        evs = con.execute("SELECT kind FROM events WHERE task=?", (t["task_id"],)).fetchall()
    assert [e["kind"] for e in evs] == ["helper_denied"]


def test_gemini_helper_request_format(monkeypatch):
    import json
    from pilot.helper import GeminiHelper, make_helper

    recorded = {}

    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self):
            return b'{"candidates": [{"content": {"parts": [{"text": "Consider the base case."}]}}]}'

    def fake_urlopen(req, timeout=30):
        recorded["url"] = req.full_url
        recorded["data"] = json.loads(req.data.decode("utf-8"))
        recorded["headers"] = dict(req.headers)
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-123")

    h = make_helper()
    assert isinstance(h, GeminiHelper)
    task = dict(id="p01", title="Sum evens", prompt="Sum all evens", signature="sum_evens(xs)")
    reply = h.reply("hints", task, "I need help", "def sum_evens(xs): pass")
    assert h.model == "gemini-3.8-flash"
    assert "gemini-3.8-flash:generateContent" in recorded["url"]
    assert reply == "Consider the base case."
    assert "key=test-key-123" in recorded["url"]
    assert recorded["data"]["generationConfig"]["maxOutputTokens"] == 600
    assert recorded["data"]["contents"][0]["role"] == "user"


def test_practice_multi_try_and_passed_first_filter(client):
    c, eng = client
    u = join(c)
    for _ in range(STUDY["anchors"]):
        solve_current(c, eng, u, ok=True)
    t = c.post("/api/next", json={}, headers=hdr(u)).json
    assert t["kind"] == "practice"
    assert t["attempts"] == 0
    assert t["max_attempts"] == 3

    # Attempt 1: wrong return value -> should fail and NOT finish the task, revealing test results
    with eng.tx() as con:
        ex_id = con.execute("SELECT ex_id FROM tasks WHERE id=?", (t["task_id"],)).fetchone()[0]
    ex = X.BANK[ex_id]
    wrong_fn = f"def {ex.fname}(*a):\n    return 'wrong'\n"
    r1 = c.post("/api/submit", json={"task_id": t["task_id"], "code": wrong_fn}, headers=hdr(u)).json
    assert r1["passed"] is False
    assert r1["done"] is False
    assert r1["attempts"] == 1
    assert r1["passed_first"] is False
    assert len(r1["details"]) > 2
    assert not all(d["ok"] for d in r1["details"])

    # /api/next returns the same pending task with attempts=1
    t_again = c.post("/api/next", json={}, headers=hdr(u)).json
    assert t_again["task_id"] == t["task_id"]
    assert t_again["attempts"] == 1

    # Attempt 2: solve correctly -> should pass and finish the task
    with eng.tx() as con:
        ex_id = con.execute("SELECT ex_id FROM tasks WHERE id=?", (t["task_id"],)).fetchone()[0]
    r2 = c.post("/api/submit", json={"task_id": t["task_id"], "code": SOL[ex_id]}, headers=hdr(u)).json
    assert r2["passed"] is True
    assert r2["done"] is True
    assert r2["attempts"] == 2
    assert r2["passed_first"] is False

    with eng.tx() as con:
        row = con.execute("SELECT * FROM tasks WHERE id=?", (t["task_id"],)).fetchone()
        assert row["passed"] == 1
        assert row["passed_first"] == 0
        assert row["attempts"] == 2
        assert row["done"] is not None


def test_practice_exhausts_attempts(client):
    c, eng = client
    u = join(c)
    for _ in range(STUDY["anchors"]):
        solve_current(c, eng, u, ok=True)
    t = c.post("/api/next", json={}, headers=hdr(u)).json
    assert t["kind"] == "practice"

    r1 = c.post("/api/submit", json={"task_id": t["task_id"], "code": WRONG}, headers=hdr(u)).json
    assert r1["done"] is False and r1["attempts"] == 1
    r2 = c.post("/api/submit", json={"task_id": t["task_id"], "code": WRONG}, headers=hdr(u)).json
    assert r2["done"] is False and r2["attempts"] == 2
    r3 = c.post("/api/submit", json={"task_id": t["task_id"], "code": WRONG}, headers=hdr(u)).json
    assert r3["done"] is True and r3["attempts"] == 3 and r3["passed"] is False

    r4 = c.post("/api/submit", json={"task_id": t["task_id"], "code": WRONG}, headers=hdr(u))
    assert r4.status_code == 404


def test_claude_helper_default_model_and_messages(monkeypatch):
    import sys
    from unittest.mock import MagicMock
    from pilot.helper import ClaudeHelper

    mock_anthropic = MagicMock()
    mock_client = MagicMock()
    mock_anthropic.Anthropic.return_value = mock_client
    monkeypatch.setitem(sys.modules, 'anthropic', mock_anthropic)

    h = ClaudeHelper()
    assert h.model == 'claude-3-7-sonnet-latest'

    # Test multi-turn message formatting
    mock_resp = MagicMock()
    mock_block = MagicMock()
    mock_block.type = 'text'
    mock_block.text = 'Here is a hint.'
    mock_resp.content = [mock_block]
    mock_client.messages.create.return_value = mock_resp

    task = dict(id='p01', title='Sum evens', prompt='Sum all evens', signature='sum_evens(xs)')
    history = [dict(request='how to start?', response='think of a loop')]
    reply = h.reply('hints', task, 'is this right?', 'def sum_evens(xs): pass', history=history)

    assert reply == 'Here is a hint.'
    call_kwargs = mock_client.messages.create.call_args[1]
    msgs = call_kwargs['messages']
    assert len(msgs) == 3
    assert msgs[0]['role'] == 'user' and 'how to start?' in msgs[0]['content'] and 'Sum evens' in msgs[0]['content']
    assert msgs[1]['role'] == 'assistant' and msgs[1]['content'] == 'think of a loop'
    assert msgs[2]['role'] == 'user' and 'is this right?' in msgs[2]['content']


def test_helper_multi_turn_history_in_study(client):
    c, eng = client
    u = join(c)
    with eng.tx() as con:
        con.execute("UPDATE users SET arm='always_on' WHERE id=?", (u["user"],))
    for _ in range(STUDY["anchors"]):
        solve_current(c, eng, u, ok=True)
    t = c.post("/api/next", json={}, headers=hdr(u)).json
    assert t["kind"] == "practice" and t["helper"] is True

    # First turn
    r1 = c.post("/api/helper", json={"task_id": t["task_id"], "message": "First question", "code": "pass"}, headers=hdr(u))
    assert r1.status_code == 200
    # Second turn
    r2 = c.post("/api/helper", json={"task_id": t["task_id"], "message": "Second question", "code": "pass"}, headers=hdr(u))
    assert r2.status_code == 200

    calls = [call for call in eng.helper.calls if call["task"]["id"] == t.get("task_id", "")]
    # eng.helper is StubHelper; check calls recorded
    last_call = eng.helper.calls[-1]
    assert last_call["message"] == "Second question"
    assert len(last_call["history"]) == 1
    assert last_call["history"][0]["request"] == "First question"


def test_helper_retry_on_violation(tmp_path):
    from pilot.helper import StubHelper
    from pilot.study_app import create_app

    class ViolatingThenFixedHelper(StubHelper):
        def __init__(self):
            super().__init__()
            self.attempt = 0

        def reply(self, tier, task, message, code, history=None, ref=None):
            self.attempt += 1
            if self.attempt == 1:
                # Violating code (more than 3 lines in hints tier)
                return "```python\nx = 1\ny = 2\nk = 3\nw = 4v = 5\n```"
            # Reprompt succeeded
            return "Here is a conceptual hint without leaking code."

    helper = ViolatingThenFixedHelper()
    app = create_app(str(tmp_path / "test_retry.db"), helper)
    c, eng = app.test_client(), app.engine

    u = join(c)
    with eng.tx() as con:
        con.execute("UPDATE users SET arm='always_on' WHERE id=?", (u["user"],))
    for _ in range(STUDY["anchors"]):
        solve_current(c, eng, u, ok=True)
    t = c.post("/api/next", json={}, headers=hdr(u)).json
    with eng.tx() as con:
        con.execute("UPDATE tasks SET tier='hints' WHERE id=?", (t["task_id"],))

    r = c.post("/api/helper", json={"task_id": t["task_id"], "message": "help", "code": "pass"}, headers=hdr(u)).json
    assert r["reply"] == "Here is a conceptual hint without leaking code."
    assert helper.attempt == 2


def test_resume_session_with_6_char_code(client):
    c, eng = client
    u = join(c)
    assert "resume_code" in u
    code = u["resume_code"]
    assert len(code) == 6 and code.isalnum()

    # Resume with correct code
    res = c.post("/api/resume", json={"resume_code": code})
    assert res.status_code == 200
    assert res.json["user"] == u["user"]
    assert res.json["resume_code"] == code

    # Resume with lower-case code is case-insensitive
    res_lower = c.post("/api/resume", json={"resume_code": code.lower()})
    assert res_lower.status_code == 200
    assert res_lower.json["user"] == u["user"]

    # Resume with bad code
    res_bad = c.post("/api/resume", json={"resume_code": "INVALID"})
    assert res_bad.status_code == 404

    # Status returns resume code
    status_resp = c.get("/api/status", headers=hdr(u)).json
    assert status_resp["resume_code"] == code


def test_right_sized_study_protocol_transitions(client):
    from pilot.config import STUDY
    assert STUDY["anchors"] == 8
    assert STUDY["assess_n"] == 4
    assert STUDY["practice_total"] == 20
    assert STUDY["assess_b_after"] == 8
    assert STUDY["assess_c_after"] == 20

    c, eng = client
    u = join(c)
    kinds = []
    for _ in range(50):
        t = c.post("/api/next", json={}, headers=hdr(u)).json
        if t.get("done"):
            break
        kinds.append(t["kind"])
        solve_current(c, eng, u, ok=True)

    # Invariants of the 32/36-task protocol:
    # 8 anchors -> 8 practice -> 4 assess_b -> 12 practice -> 4 assess_c = 36 items total
    assert kinds[:8] == ["anchor"] * 8
    assert kinds[8:16] == ["practice"] * 8
    assert kinds[16:20] == ["assess_b"] * 4
    assert kinds[20:32] == ["practice"] * 12
    assert kinds[32:36] == ["assess_c"] * 4
    assert len(kinds) == 36


def test_unassisted_probe_has_focus_and_logs_blur_telemetry(client):
    c, eng = client
    u = join(c)
    with eng.tx() as con:
        con.execute("UPDATE users SET arm='fixed_drills' WHERE id=?", (u["user"],))
    for _ in range(STUDY["anchors"]):
        solve_current(c, eng, u, ok=True)

    for _ in range(STUDY["drill_every"] - 1):
        solve_current(c, eng, u, ok=True)

    probe = c.post("/api/next", json={}, headers=hdr(u)).json
    assert probe["kind"] == "practice"
    assert probe["tier"] == "off"
    assert probe["off"] is True
    assert probe["lockdown"] is False
    assert probe["focus"] is True

    r = c.post("/api/event", json={"task_id": probe["task_id"], "kind": "blur"}, headers=hdr(u))
    assert r.status_code == 200

    with eng.tx() as con:
        ex_id = con.execute("SELECT ex_id FROM tasks WHERE id=?", (probe["task_id"],)).fetchone()[0]
    sub = c.post("/api/submit", json={"task_id": probe["task_id"], "code": SOL[ex_id]}, headers=hdr(u)).json
    assert sub["passed"] is True

    with eng.tx() as con:
        row = con.execute("SELECT suspect, trusted FROM tasks WHERE id=?", (probe["task_id"],)).fetchone()
        assert row["suspect"] == 1
