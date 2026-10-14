"""Participant engine: connects the thermostat to the task flow. No HTTP in here.

Flow: a trusted locked baseline round -> practice tasks. For each practice task the thermostat decides
assisted (with a help level) or locked (a probe, or a trusted sentinel). Locked rounds disable the helper and
count paste attempts; a locked round with paste attempts is excluded from the skill estimate. High-stakes
tasks always get full help and are never probed. State lives in an event log and is rebuilt by replay.
"""
import json
import os
import random
from dataclasses import dataclass, field

import numpy as np

from skill_thermostat import SkillFilter, Thermostat, ThermostatConfig
from skill_thermostat.model import GRID
from skill_thermostat.sim import C_GRID, DELTA, S_MAX

from . import scoring
from .tasks import BY_ID, TASKS, public_view


def level_name(alpha):
    return "hints" if alpha < 0.34 else "guided" if alpha < 0.67 else "full"


@dataclass
class EngineConfig:
    thermostat: ThermostatConfig = field(default_factory=lambda: ThermostatConfig(sentinel_rate=0.03))
    wide_shift: float = -0.04
    baseline_items: int = 6        # a real pilot should use 20-30 (needs a far bigger task bank)
    s_max: float = S_MAX
    delta: float = DELTA


def load_config(path=None):
    """Read a sweep_pick.json ({cfg, shift}) if present, else the default robust configuration."""
    if path and os.path.exists(path):
        p = json.load(open(path))
        return EngineConfig(thermostat=ThermostatConfig(**p["cfg"]), wide_shift=p.get("shift", -0.04))
    return EngineConfig()


def pick_baseline(k, s_max=S_MAX):
    elig = sorted((t for t in TASKS if t["stakes"] <= s_max), key=lambda t: t["difficulty"])
    idx = sorted(set(np.linspace(0, len(elig) - 1, k).round().astype(int).tolist()))
    return [elig[i]["id"] for i in idx]


class Participant:
    def __init__(self, store, pid, seed, cfg, assistant):
        self.store, self.pid, self.cfg, self.assistant = store, pid, cfg, assistant
        self.rng = random.Random(seed)
        self.F = SkillFilter(1, GRID, c_grid=C_GRID, robust_drift=True, wide_shift=cfg.wide_shift)
        self.ctl = Thermostat(cfg.thermostat, GRID)
        self.baseline_ids = pick_baseline(cfg.baseline_items, cfg.s_max)
        self.baseline_done, self.floor_hat = 0, None
        self.ae_acc, self.n_practice = 0.0, 0
        self.seen, self.pending, self.recent = set(), None, []
        self.helps = 0

    # ------------------------------------------------------------ event application (live and replay)
    def _apply(self, kind, p):
        if kind == "serve":
            self.pending = p
        elif kind == "help":
            self.helps += 1
        elif kind == "submit":
            if p["mode"] == "locked" and not p["excluded"]:
                self.F.update(np.array([p["d"]]), np.array([p["y"]]), np.array([True]),
                              trusted=np.array([p["trusted"]]))
            if not p["excluded"]:
                self.seen.add(p["task_id"])
            if p["phase"] == "baseline":
                if not p["excluded"]:
                    self.baseline_done += 1
                    if self.baseline_done == self.cfg.baseline_items:
                        self.floor_hat = float(self.F.summary().mean[0]) - self.cfg.delta
            else:
                self.ae_acc += 0.0 if p["mode"] == "locked" else p["alpha"]
                self.n_practice += 1
                self.recent = (self.recent + [p["mode"]])[-10:]
                if self.n_practice % 10 == 0:
                    self.F.predict(wide=np.array([self.ae_acc / 10 > 0.5]))
                    self.ae_acc = 0.0
            self.pending = None

    def _log(self, kind, payload):
        self.store.add_event(self.pid, kind, payload)
        self._apply(kind, payload)

    def replay(self):
        for _, kind, p in self.store.events(self.pid):
            self._apply(kind, p)

    # ------------------------------------------------------------------------------------- actions
    def phase(self):
        return "baseline" if self.baseline_done < self.cfg.baseline_items else "practice"

    def serve(self):
        """Pick the next task and decide its mode. Idempotent while a task is pending."""
        if self.pending is None:
            if self.phase() == "baseline":
                tid = next(t for t in self.baseline_ids if t not in self.seen)
                p = dict(task_id=tid, mode="locked", trusted=True, alpha=0.0, phase="baseline",
                         d=BY_ID[tid]["difficulty"], repeat=False)
            else:
                summ = self.F.summary()
                unseen = [t for t in TASKS if t["id"] not in self.seen]
                pool, repeat = (unseen, False) if unseen else (TASKS, True)
                target = float(summ.mean[0]) + 0.15
                task = min(pool, key=lambda t: (abs(t["difficulty"] - target), self.rng.random()))
                alpha, off, sent = self.ctl.decide(
                    summ, np.array([self.floor_hat]), np.array([task["stakes"] <= self.cfg.s_max]),
                    np.array([self.rng.random()]), np.array([self.rng.random()]))
                p = dict(task_id=task["id"], mode="locked" if off[0] else "assisted", trusted=bool(sent[0]),
                         alpha=float(alpha[0]), phase="practice", d=task["difficulty"], repeat=repeat)
            self._log("serve", p)
        return self.view_pending()

    def view_pending(self):
        p = self.pending
        return dict(task=public_view(BY_ID[p["task_id"]]), mode=p["mode"], phase=p["phase"],
                    supervised=p["trusted"] and p["phase"] == "practice",
                    level=None if p["mode"] == "locked" else level_name(p["alpha"]))

    def submit(self, code, paste_attempts=0, burst_inserts=0, secs=None):
        if self.pending is None:
            raise ValueError("no task is pending")
        p = self.pending
        res = scoring.run_tests(code, BY_ID[p["task_id"]])
        excluded = p["mode"] == "locked" and (paste_attempts > 0 or burst_inserts > 0)
        self._log("submit", dict(task_id=p["task_id"], y=bool(res["ok"]), passed=res["passed"], total=res["total"],
                                 mode=p["mode"], trusted=p["trusted"], alpha=p["alpha"], phase=p["phase"],
                                 d=p["d"], repeat=p["repeat"], paste_attempts=int(paste_attempts),
                                 burst_inserts=int(burst_inserts), secs=secs, excluded=excluded))
        return dict(ok=res["ok"], passed=res["passed"], total=res["total"], error=res["error"],
                    excluded=excluded)

    def help(self, code, message):
        p = self.pending
        if p is None or p["mode"] != "assisted":
            raise PermissionError("the helper is off for this round")
        level = level_name(p["alpha"])
        text = self.assistant.reply(BY_ID[p["task_id"]], code, message, level)
        self._log("help", dict(task_id=p["task_id"], level=level))
        return dict(reply=text, level=level)

    def state(self):
        s = self.F.summary()
        out = dict(phase=self.phase(), baseline_done=self.baseline_done, baseline_total=self.cfg.baseline_items,
                   practice_done=self.n_practice, recent_modes=self.recent)
        if self.floor_hat is not None:
            out.update(skill=round(float(s.mean[0]), 2), lower_bound=round(float(s.q10[0]), 2),
                       floor=round(self.floor_hat, 2), margin=round(float(s.q10[0]) - self.floor_hat, 2),
                       probe_integrity=round(1.0 - float(s.c_mean[0]), 2))
        return out
