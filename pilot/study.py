"""Study engine: arms, phases, Computerized Adaptive Testing (CAT) baseline, thermostat control and persistence (SQLite)."""
import json
import secrets
import sqlite3
import time
from contextlib import contextmanager

import numpy as np
from scipy.special import ndtr

from skill_thermostat import SkillFilter, Thermostat
from skill_thermostat.model import A_DISC, GRID

from . import config
from . import exercises as X
from . import runner
from .config import C_GRID, CONTROLLER, DELTA, STUDY, WIDE_SD, WIDE_SHIFT
from .helper import make_helper, scrub, violates
from .verdict import LOOKBACK, MIN_OBS, MIN_PROBES, STALE_AFTER, decide

ARMS = ("thermostat", "always_on", "fixed_drills")
POOL_OF = {"anchor": "A", "assess_b": "B", "assess_c": "C", "practice": "P"}
COUNTER = {"anchor": "n_anchor", "practice": "n_practice", "assess_b": "n_assess_b", "assess_c": "n_assess_c"}
EVENT_KINDS = ("paste", "paste_blocked", "drop_blocked", "blur", "focus", "run")
PASTE_SUSPECT_CHARS = 40

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id TEXT PRIMARY KEY, arm TEXT NOT NULL, created REAL, seed INTEGER, consent INTEGER,
  n_anchor INTEGER DEFAULT 0, n_practice INTEGER DEFAULT 0, n_assess_b INTEGER DEFAULT 0, n_assess_c INTEGER DEFAULT 0,
  floor_hat REAL, post BLOB, ae_acc REAL DEFAULT 0, ae_n INTEGER DEFAULT 0, floor_abs REAL);
CREATE TABLE IF NOT EXISTS tasks(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT NOT NULL, ex_id TEXT, kind TEXT, tier TEXT, lockdown INTEGER,
  trusted INTEGER, alpha REAL, off INTEGER, sentinel INTEGER, urgent INTEGER, issued REAL, done REAL, passed INTEGER,
  tests_passed INTEGER, tests_total INTEGER, suspect INTEGER DEFAULT 0, code TEXT,
  attempts INTEGER DEFAULT 0, passed_first INTEGER);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, task INTEGER, ts REAL, kind TEXT, data TEXT);
CREATE TABLE IF NOT EXISTS skill_log(id INTEGER PRIMARY KEY AUTOINCREMENT, user TEXT, task INTEGER, ts REAL, n INTEGER,
  mean REAL, sd REAL, q10 REAL);
CREATE TABLE IF NOT EXISTS helper_log(id INTEGER PRIMARY KEY AUTOINCREMENT, task INTEGER, ts REAL, tier TEXT,
  request TEXT, response TEXT);
"""


class EngineError(Exception):
    status = 400


class Forbidden(EngineError):
    status = 403


class NotFound(EngineError):
    status = 404


def _fisher_info_item(pg, d_val, a=A_DISC):
    """Posterior expected Fisher information for an unassisted item of difficulty d_val."""
    z = a * (GRID - d_val)
    p = np.clip(ndtr(z), 1e-9, 1.0 - 1e-9)
    phi2 = np.exp(-z * z) / (2.0 * np.pi)
    info_grid = (a * a * phi2) / (p * (1.0 - p))
    return float(pg @ info_grid)


class Engine:
    def __init__(self, db_path, helper=None):
        self.db_path = db_path
        self.helper = helper or make_helper({e.id: e.ref for e in X.ALL})
        self.ctl = Thermostat(CONTROLLER, GRID)
        con = sqlite3.connect(db_path, timeout=30)
        con.execute("PRAGMA journal_mode=WAL")
        con.executescript(SCHEMA)
        for col, col_def in [("floor_abs", "REAL")]:
            try:
                con.execute(f"ALTER TABLE users ADD COLUMN {col} {col_def}")
            except sqlite3.OperationalError:
                pass
        for col, col_def in [("attempts", "INTEGER DEFAULT 0"), ("passed_first", "INTEGER")]:
            try:
                con.execute(f"ALTER TABLE tasks ADD COLUMN {col} {col_def}")
            except sqlite3.OperationalError:
                pass
        con.close()

    # ---------------------------------------------------------------- plumbing
    @contextmanager
    def tx(self):
        con = sqlite3.connect(self.db_path, timeout=30, isolation_level=None)
        con.row_factory = sqlite3.Row
        con.execute("BEGIN IMMEDIATE")
        try:
            yield con
        except BaseException:
            con.execute("ROLLBACK")
            raise
        else:
            con.execute("COMMIT")
        finally:
            con.close()

    @staticmethod
    def _new_filter():
        return SkillFilter(1, GRID, c_grid=C_GRID, robust_drift=True, wide_shift=WIDE_SHIFT, wide_sd=WIDE_SD)

    def _filter(self, u):
        F = self._new_filter()
        F.post = np.frombuffer(u["post"], dtype=np.float64).reshape(1, len(GRID), len(C_GRID)).copy()
        return F

    @staticmethod
    def _user(c, uid):
        u = c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        if u is None:
            raise NotFound("unknown user")
        return u

    @staticmethod
    def _pending(c, uid, task_id):
        t = c.execute("SELECT * FROM tasks WHERE id=? AND user=? AND done IS NULL", (task_id, uid)).fetchone()
        if t is None:
            raise NotFound("no such pending task")
        return t

    @staticmethod
    def _suspicious(kind, data):
        if kind in ("paste_blocked", "drop_blocked", "blur"):
            return True
        if kind == "paste":
            try:
                return json.loads(data or "{}").get("chars", 0) >= PASTE_SUSPECT_CHARS
            except ValueError:
                return True
        return False

    @staticmethod
    def _next_kind(u):
        s = STUDY
        if u["n_anchor"] < s["anchors"]:
            return "anchor"
        if u["n_practice"] >= s["assess_b_after"] and u["n_assess_b"] < s["assess_n"]:
            return "assess_b"
        if u["n_practice"] >= s["assess_c_after"] and u["n_assess_c"] < s["assess_n"]:
            return "assess_c"
        if u["n_practice"] < s["practice_total"]:
            return "practice"
        return None

    @staticmethod
    def plan(seed):
        """Per-learner fixed forms: initial Pool A ordering and matched B/C pairs, drawn from the user's seed."""
        rng = np.random.default_rng([seed, 7919])
        a_ids = [e.id for e in X.pool("A")]
        anchors = [a_ids[i] for i in rng.permutation(len(a_ids))[:STUDY["anchors"]]]
        b_ids = sorted(e.id for e in X.pool("B"))
        pairs = [b_ids[i] for i in sorted(rng.permutation(len(b_ids))[:STUDY["assess_n"]])]
        return dict(anchor=anchors, assess_b=pairs, assess_c=["c" + b[1:] for b in pairs])

    @staticmethod
    def _cat_pick_anchor(F, seen, rng):
        """Computerized Adaptive Testing (CAT): select the unseen Pool A item that maximizes
        posterior expected Fisher information, with slight randomization among the top-2 items
        for item-exposure balance."""
        pg = F.post[0].sum(axis=1)
        candidates = [e for e in X.pool("A") if e.id not in seen]
        scored = sorted(
            candidates,
            key=lambda e: (-round(_fisher_info_item(pg, e.d), 6), float(rng.random()))
        )
        # First anchor starts at median difficulty; subsequent anchors pick the top Fisher-information item
        return scored[0]

    @staticmethod
    def _view(t):
        ex = X.BANK[t["ex_id"]]
        starter = t["code"] if ("code" in t.keys() and t["code"]) else ex.starter
        max_attempts = STUDY.get("practice_max_attempts", 3) if t["kind"] == "practice" else 1
        attempts = t["attempts"] if ("attempts" in t.keys() and t["attempts"]) else 0
        return dict(task_id=t["id"], kind=t["kind"], title=ex.title, prompt=ex.prompt,
                    signature=f"{ex.fname}({ex.params})", starter=starter, examples=ex.examples(),
                    tier=t["tier"], focus=bool(t["lockdown"]), helper=t["tier"] != "off", urgent=bool(t["urgent"]),
                    attempts=attempts, max_attempts=max_attempts)

    # ---------------------------------------------------------------- study flow
    def join(self, consent, floor_abs=None):
        """floor_abs: an absolute skill standard for this person (e.g. a role requirement) instead of baseline - DELTA."""
        if not consent:
            raise EngineError("consent is required")
        uid, rnd = secrets.token_hex(8), secrets.SystemRandom()
        with self.tx() as c:
            counts = {a: c.execute("SELECT COUNT(*) FROM users WHERE arm=?", (a,)).fetchone()[0] for a in ARMS}
            arm = min(ARMS, key=lambda a: (counts[a], rnd.random()))    # blocked randomization
            c.execute("INSERT INTO users(id, arm, created, seed, consent, post, floor_abs) VALUES (?,?,?,?,1,?,?)",
                      (uid, arm, time.time(), rnd.randrange(2 ** 31), self._new_filter().post.tobytes(), floor_abs))
        return dict(user=uid, arm=arm)

    def next_task(self, uid, urgent=False):
        with self.tx() as c:
            u = self._user(c, uid)
            pend = c.execute("SELECT * FROM tasks WHERE user=? AND done IS NULL", (uid,)).fetchone()
            if pend:
                return self._view(pend)
            kind = self._next_kind(u)
            if kind is None:
                return dict(done=True)
            n_issued = c.execute("SELECT COUNT(*) FROM tasks WHERE user=?", (uid,)).fetchone()[0]
            rng = np.random.default_rng([u["seed"], n_issued])
            F = self._filter(u)
            summ = F.summary()
            seen = {r[0] for r in c.execute("SELECT ex_id FROM tasks WHERE user=?", (uid,))}

            alpha, off, sent, is_urgent = 1.0, False, False, False
            if kind == "practice":
                recent = c.execute("SELECT urgent FROM tasks WHERE user=? AND kind='practice' ORDER BY id DESC LIMIT ?",
                                   (uid, STUDY["urgent_window"])).fetchall()
                is_urgent = bool(urgent) and sum(r[0] for r in recent) < STUDY["urgent_max"]
                elig = not is_urgent    # urgent tasks always get full help and are never measured
                u_prb, u_snt = float(rng.random()), float(rng.random())
                if u["arm"] == "thermostat":
                    p_rows = c.execute(
                        "SELECT id, off, lockdown FROM tasks WHERE user=? AND kind='practice' AND done IS NOT NULL ORDER BY id",
                        (uid,)).fetchall()
                    n_ord_probes = sum(1 for r in p_rows if r["off"] and not r["lockdown"])
                    last_p = max((r["id"] for r in p_rows if r["off"]), default=None)
                    since = sum(1 for r in p_rows if last_p is None or r["id"] > last_p)
                    rem_prac = STUDY["practice_total"] - u["n_practice"]
                    min_req = max(MIN_PROBES, MIN_OBS)
                    need_probes = (n_ord_probes < min_req) and (rem_prac <= (min_req - n_ord_probes) * 2)
                    a, o, s = self.ctl.decide(
                        summ, np.array([u["floor_hat"]]), np.array([elig]),
                        np.array([0.0 if need_probes else u_prb]), np.array([u_snt]),
                        since_last=np.array([since]), stale_limit=STALE_AFTER - 1)
                    alpha, off, sent = float(a[0]), bool(o[0]), bool(s[0])
                elif u["arm"] == "fixed_drills":
                    off = elig and (u["n_practice"] + 1) % STUDY["drill_every"] == 0

                left = [e for e in X.pool("P") if e.id not in seen]
                if off:
                    # Unassisted probe: pick from top-3 Fisher-informative items near the decision boundary
                    pg = F.post[0].sum(axis=1)
                    left.sort(key=lambda e: -_fisher_info_item(pg, e.d))
                else:
                    # Assisted practice: Zone of Proximal Development (mean + 0.3)
                    left.sort(key=lambda e: abs(e.d - (float(summ.mean[0]) + 0.3)))
                ex = left[int(rng.integers(0, min(3, len(left))))]
            elif kind == "anchor":
                alpha, off = 0.0, True
                ex = self._cat_pick_anchor(F, seen, rng)
            else:
                alpha, off = 0.0, True
                ex = X.BANK[self.plan(u["seed"])[kind][u[COUNTER[kind]]]]

            tier = "off" if off else "full" if alpha >= 0.67 else "hints" if alpha >= 0.34 else "nudge"
            strict = int(kind != "practice" or sent)
            trusted = int(kind == "anchor" or sent)
            tid = c.execute(
                "INSERT INTO tasks(user, ex_id, kind, tier, lockdown, trusted, alpha, off, sentinel, urgent, issued, attempts, passed_first) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,0,NULL)",
                (uid, ex.id, kind, tier, strict, trusted, alpha, int(off), int(sent), int(is_urgent), time.time())).lastrowid
            return self._view(c.execute("SELECT * FROM tasks WHERE id=?", (tid,)).fetchone())

    def log_event(self, uid, task_id, kind, data=None):
        if kind not in EVENT_KINDS:
            raise EngineError("unknown event kind")
        with self.tx() as c:
            self._pending(c, uid, task_id)
            c.execute("INSERT INTO events(task, ts, kind, data) VALUES (?,?,?,?)",
                      (task_id, time.time(), kind, json.dumps(data or {})))

    def run_examples(self, uid, task_id, code):
        with self.tx() as c:
            t = self._pending(c, uid, task_id)
        ex = X.BANK[t["ex_id"]]
        res = runner.run_cases(code, ex.fname, ex.cases[:2], ex.expected()[:2])
        return dict(error=res["fatal"], results=[\
            dict(call=e["call"], expected=e["expected"], got=d["got"], ok=d["ok"], err=d["err"])\
            for e, d in zip(ex.examples(), res["details"])])

    def submit(self, uid, task_id, code):
        with self.tx() as c:
            self._user(c, uid)
            t = self._pending(c, uid, task_id)
        ex = X.BANK[t["ex_id"]]
        res = runner.run_cases(code, ex.fname, ex.cases, ex.expected())      # outside the write lock
        with self.tx() as c:
            u = self._user(c, uid)
            t = self._pending(c, uid, task_id)                               # re-check: another submit may have won
            passed = int(res["ok"])
            kind, off = t["kind"], bool(t["off"])
            max_attempts = STUDY.get("practice_max_attempts", 3) if kind == "practice" else 1
            cur_attempts = (t["attempts"] or 0) + 1
            passed_first = passed if cur_attempts == 1 else (t["passed_first"] if t["passed_first"] is not None else passed)
            is_done = bool(passed) or (cur_attempts >= max_attempts)

            if not is_done:
                c.execute("UPDATE tasks SET attempts=?, passed_first=?, code=?, tests_passed=?, tests_total=? WHERE id=?",
                          (cur_attempts, passed_first, code, res["passed"], res["total"], task_id))
                details = [
                    dict(call=f"{ex.fname}({', '.join(repr(a) for a in c_args)})",
                         expected=json.dumps(e),
                         got=dd["got"],
                         ok=dd["ok"],
                         err=dd["err"])
                    for c_args, e, dd in zip(ex.cases, ex.expected(), res["details"])
                ]
                visible = details[:2]
                return dict(passed=False, done=False, attempts=cur_attempts, max_attempts=max_attempts,
                            passed_first=bool(passed_first), tests_passed=res["passed"], tests_total=res["total"],
                            error=res["fatal"], visible=visible, details=details)

            evs = c.execute("SELECT kind, data FROM events WHERE task=?", (task_id,)).fetchall()
            suspect = int(any(self._suspicious(e["kind"], e["data"]) for e in evs))
            trusted = int(bool(t["trusted"]) and not suspect)
            F = self._filter(u)
            d, one = np.array([ex.d]), np.array([True])
            floor_hat, ae_acc, ae_n = u["floor_hat"], u["ae_acc"], u["ae_n"]
            n_after = u[COUNTER[kind]] + 1
            measured = kind == "anchor" or (kind == "practice" and off)
            if kind == "anchor":
                F.update(d, np.array([bool(passed)]), one, trusted=np.array([bool(trusted)]))
                if n_after == STUDY["anchors"]:
                    if u["floor_abs"] is not None:
                        floor_hat = u["floor_abs"]
                    else:
                        base = F.summary()
                        ds = [e.d for e in X.pool("A")]
                        est = float((base.mean if config.FLOOR_RULE == "mean" else base.q10)[0])
                        # Top-clip at max(ds) so perfect scorers are not penalized by the grid ceiling;
                        # never bottom-clip above the learner's own q10 so weak learners are not locked out.
                        raw_floor = min(est, max(ds)) - DELTA
                        floor_hat = min(raw_floor, float(base.q10[0]) - 0.05)
            elif kind == "practice":
                if off:
                    F.update(d, np.array([bool(passed_first)]), one, trusted=np.array([bool(trusted)]))
                ae_acc += 0.0 if off else t["alpha"]
                ae_n += 1
                if ae_n == 10:      # same cadence as the simulator: drift step every 10 tasks
                    F.predict(wide=np.array([ae_acc / 10 > 0.5]))
                    ae_acc, ae_n = 0.0, 0
            # assessments are outcome measures only: they never feed the filter
            if measured:
                sm = F.summary()
                n_meas = c.execute("SELECT COUNT(*) FROM skill_log WHERE user=?", (uid,)).fetchone()[0] + 1
                c.execute("INSERT INTO skill_log(user, task, ts, n, mean, sd, q10) VALUES (?,?,?,?,?,?,?)",
                          (uid, task_id, time.time(), n_meas, float(sm.mean[0]), float(sm.sd[0]), float(sm.q10[0])))
            c.execute(f"UPDATE users SET {COUNTER[kind]}=?, floor_hat=?, post=?, ae_acc=?, ae_n=? WHERE id=?",
                      (n_after, floor_hat, F.post.tobytes(), ae_acc, ae_n, uid))
            c.execute("UPDATE tasks SET done=?, passed=?, tests_passed=?, tests_total=?, suspect=?, trusted=?, code=?, "
                      "attempts=?, passed_first=? WHERE id=?",
                      (time.time(), passed, res["passed"], res["total"], suspect, trusted, code,
                       cur_attempts, passed_first, task_id))

        details = [
            dict(call=f"{ex.fname}({', '.join(repr(a) for a in c_args)})",
                 expected=json.dumps(e),
                 got=dd["got"],
                 ok=dd["ok"],
                 err=dd["err"])
            for c_args, e, dd in zip(ex.cases, ex.expected(), res["details"])
        ] if kind == "practice" else None
        visible = [dict(call=e["call"], expected=e["expected"], got=dd["got"], ok=dd["ok"], err=dd["err"])
                   for e, dd in zip(ex.examples(), res["details"])]
        return dict(passed=bool(passed), done=True, attempts=cur_attempts, max_attempts=max_attempts,
                    passed_first=bool(passed_first), tests_passed=res["passed"], tests_total=res["total"],
                    error=res["fatal"], visible=visible, details=details if details is not None else visible)

    def ask_helper(self, uid, task_id, message, code):
        denied = False
        with self.tx() as c:
            self._user(c, uid)
            t = self._pending(c, uid, task_id)
            if t["tier"] == "off":
                c.execute("INSERT INTO events(task, ts, kind, data) VALUES (?,?,'helper_denied','{}')", (task_id, time.time()))
                denied = True
            else:
                n = c.execute("SELECT COUNT(*) FROM helper_log WHERE task=?", (task_id,)).fetchone()[0]
                if n >= STUDY["helper_max_per_task"]:
                    raise Forbidden("helper limit reached for this task")
                rows = c.execute("SELECT request, response FROM helper_log WHERE task=? ORDER BY id", (task_id,)).fetchall()
                history = [dict(request=r["request"], response=r["response"]) for r in rows]
        if denied:
            raise Forbidden("the AI helper is off for this task")
        ex = X.BANK[t["ex_id"]]
        task = dict(id=ex.id, title=ex.title, prompt=ex.prompt, signature=f"{ex.fname}({ex.params})")
        reply_raw = self.helper.reply(t["tier"], task, message, code, history=history, ref=ex.ref)
        if violates(t["tier"], reply_raw, ex.ref):
            correction = (
                f"Your previous response violated our strict pedagogy rules for '{t['tier']}' tier. "
                + ("For 'hints' mode: explain concepts or errors, do NOT provide a complete solution, "
                   "and at most 3 short lines of code to illustrate an idea. " if t["tier"] == "hints" else
                   "For 'nudge' mode: reply with ONE short conceptual nudge or a single Socratic question in at most two sentences. Write NO code. ")
                + "Please rewrite your answer now complying strictly with these constraints."
            )
            try:
                retry_reply = self.helper.reply(t["tier"], task, correction, code, history=history, ref=ex.ref)
                if not violates(t["tier"], retry_reply, ex.ref):
                    reply_raw = retry_reply
            except Exception:
                pass
        text = scrub(t["tier"], reply_raw, ex.ref)
        with self.tx() as c:
            self._pending(c, uid, task_id)
            n = c.execute("SELECT COUNT(*) FROM helper_log WHERE task=?", (task_id,)).fetchone()[0]
            if n >= STUDY["helper_max_per_task"]:
                raise Forbidden("helper limit reached for this task")
            c.execute("INSERT INTO helper_log(task, ts, tier, request, response) VALUES (?,?,?,?,?)",
                      (task_id, time.time(), t["tier"], message, text))
        return dict(tier=t["tier"], reply=text)

    def status(self, uid):
        with self.tx() as c:
            u = self._user(c, uid)
            return dict(next=self._next_kind(u) or "done", anchors=u["n_anchor"], practice=u["n_practice"],
                        assess_b=u["n_assess_b"], assess_c=u["n_assess_c"])

    def verdict(self, uid):
        """Keep-using-AI / cut-back verdict for one person (see pilot/verdict.py). None until the baseline is complete."""
        with self.tx() as c:
            u = self._user(c, uid)
            if u["floor_hat"] is None:
                return None
            log = c.execute("SELECT mean FROM skill_log WHERE user=? ORDER BY id", (uid,)).fetchall()
            done = c.execute("SELECT id, ex_id, kind, off, lockdown, trusted, suspect, passed FROM tasks "
                             "WHERE user=? AND done IS NOT NULL ORDER BY id", (uid,)).fetchall()
            s = self._filter(u).summary()
        mean, trend = float(s.mean[0]), 0.0
        if len(log) > LOOKBACK:
            trend = log[-1][0] - log[-1 - LOOKBACK][0]
        unassisted = [t for t in done if t["off"] and t["kind"] in ("anchor", "practice")]
        probes = [t for t in unassisted if t["kind"] == "practice"]
        ordinary = [t for t in probes if not t["lockdown"]]             # honor-system probes
        anchors = [t for t in unassisted if t["kind"] == "anchor"]
        last = max((t["id"] for t in probes), default=None)
        since = sum(1 for t in done if t["kind"] == "practice" and (last is None or t["id"] > last))

        return decide(mean, float(s.sd[0]), float(s.q10[0]), u["floor_hat"], len(log), trend, n_probes=len(probes),
                      since_last=since, relative_floor=u["floor_abs"] is None,
                      probe_suspect=(sum(t["suspect"] for t in ordinary) / len(ordinary)) if ordinary else 0.0,
                      n_probe_obs=len(ordinary),
                      anchor_suspect=(sum(t["suspect"] for t in anchors) / len(anchors)) if anchors else 0.0).as_dict()

    # ---------------------------------------------------------------- reporting
    def summary(self):
        out = []
        with self.tx() as c:
            for u in c.execute("SELECT * FROM users ORDER BY created").fetchall():
                done = c.execute("SELECT * FROM tasks WHERE user=? AND done IS NOT NULL", (u["id"],)).fetchall()

                def rate(pred):
                    xs = [t["passed"] for t in done if pred(t)]
                    return sum(xs) / len(xs) if xs else None

                helper = {r[0]: r[1] for r in c.execute(
                    "SELECT h.tier, COUNT(*) FROM helper_log h JOIN tasks t ON t.id=h.task WHERE t.user=? GROUP BY h.tier",
                    (u["id"],))}
                s = self._filter(u).summary()
                out.append(dict(
                    user=u["id"], arm=u["arm"], anchors=rate(lambda t: t["kind"] == "anchor"),
                    practice=rate(lambda t: t["kind"] == "practice"),
                    practice_first=rate(lambda t: t["kind"] == "practice" and t["passed_first"]),
                    probes=rate(lambda t: t["kind"] == "practice" and t["off"]),
                    n_probes=sum(1 for t in done if t["kind"] == "practice" and t["off"]),
                    n_sentinels=sum(1 for t in done if t["kind"] == "practice" and t["sentinel"]),
                    assess_b=rate(lambda t: t["kind"] == "assess_b"), assess_c=rate(lambda t: t["kind"] == "assess_c"),
                    helper_requests=helper, suspect_tasks=sum(t["suspect"] for t in done),
                    skill_mean=float(s.mean[0]), skill_lower=float(s.q10[0]), floor=u["floor_hat"],
                    contamination_est=float(s.c_mean[0])))
        for r in out:                    # outside the transaction above: verdict() opens its own
            r["verdict"] = self.verdict(r["user"])
        return out
