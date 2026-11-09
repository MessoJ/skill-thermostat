"""Local-Only Telemetry Ledger with Multi-Domain Posterior Scoping (Milestone 3, Step 2).

Uses only Python's standard library `sqlite3` (storing data by default in
`.thermostat.db` or `~/.local/share/skill_thermostat/ledger.db`).
Maintains independent `SkillFilter` posterior grids per `domain` (e.g., `py:algo`,
`go:ledger`, `rust:core`) while sharing a weak global hyper-prior across domains,
and steers assistance using `Thermostat.decide_hysteresis`.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

import numpy as np

from .controller import Thermostat, ThermostatConfig
from .filters import SkillFilter
from .friction import LEVEL_FULL, LEVEL_PROBE_FAULT, LEVEL_SKELETON
from .model import GRID

C_GRID = (0.0, 0.1, 0.2, 0.3, 0.4)
GENESIS_HASH = "0" * 64
DEFAULT_DOMAIN = "py:algo"
HYPER_PRIOR_WEIGHT = 0.15


def resolve_db_path(db_path: str | Path | None = None) -> Path:
    """Resolve the SQLite database path."""
    if db_path is not None:
        p = Path(db_path).expanduser()
    elif os.environ.get("THERMOSTAT_DB"):
        p = Path(os.environ["THERMOSTAT_DB"]).expanduser()
    else:
        p = Path(".thermostat.db")
    if p.parent and str(p.parent) != ".":
        p.parent.mkdir(parents=True, exist_ok=True)
    return p


def user_share_db_path() -> Path:
    """Return the XDG user-local telemetry path `~/.local/share/skill_thermostat/ledger.db`."""
    p = Path.home() / ".local" / "share" / "skill_thermostat" / "ledger.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def map_controller_level(alpha: float, off: bool) -> str:
    """Map continuous assistance alpha in [0, 1] and probe flag `off` to discrete friction mode."""
    if off or alpha < 0.34:
        return LEVEL_PROBE_FAULT
    if alpha < 0.75:
        return LEVEL_SKELETON
    return LEVEL_FULL


class Ledger:
    """SQLite telemetry ledger with per-domain Bayesian skill posteriors and 3-state hysteresis."""

    def __init__(
        self,
        db_path: str | Path | None = None,
        floor_hat: float = -0.35,
        floor_full: float = 0.25,
        probe_cadence: int = 5,
    ) -> None:
        self.db_path = resolve_db_path(db_path)
        self.floor_hat = float(floor_hat)
        self.floor_full = float(floor_full)
        self.probe_cadence = int(probe_cadence)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(str(self.db_path), timeout=15.0)
        con.row_factory = sqlite3.Row
        return con

    def _init_db(self) -> None:
        with self._connect() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    repo_hash TEXT NOT NULL,
                    intervention_mode TEXT NOT NULL,
                    prompt_tokens INTEGER NOT NULL,
                    completion_tokens INTEGER NOT NULL,
                    test_exit_code INTEGER NOT NULL,
                    time_to_green_sec REAL NOT NULL,
                    edit_distance_ratio REAL NOT NULL,
                    probe_caught INTEGER DEFAULT NULL,
                    verification_status TEXT NOT NULL DEFAULT 'VERIFIED_PASS',
                    chars_per_sec REAL NOT NULL DEFAULT 0.0,
                    domain TEXT NOT NULL DEFAULT 'py:algo',
                    event_hash TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS posteriors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    skill_mean REAL NOT NULL,
                    skill_std REAL NOT NULL,
                    controller_level TEXT NOT NULL,
                    skill_q10 REAL NOT NULL DEFAULT 0.0,
                    alpha REAL NOT NULL DEFAULT 1.0,
                    domain TEXT NOT NULL DEFAULT 'py:algo'
                );

                CREATE TABLE IF NOT EXISTS interventions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    intervention_mode TEXT NOT NULL,
                    code_hash TEXT NOT NULL,
                    clean_hash TEXT NOT NULL DEFAULT '',
                    prompt_tokens INTEGER NOT NULL DEFAULT 0,
                    completion_tokens INTEGER NOT NULL DEFAULT 0,
                    transformed_code TEXT NOT NULL DEFAULT '',
                    clean_code TEXT NOT NULL DEFAULT '',
                    fault_metadata_json TEXT NOT NULL DEFAULT '{}',
                    target_file TEXT NOT NULL DEFAULT '',
                    target_function TEXT NOT NULL DEFAULT '',
                    domain TEXT NOT NULL DEFAULT 'py:algo',
                    resolved INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS thermostat_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )
            # Schema migrations for existing SQLite databases
            ev_cols = {
                r["name"] for r in con.execute("PRAGMA table_info(events)").fetchall()
            }
            if "verification_status" not in ev_cols:
                con.execute(
                    "ALTER TABLE events ADD COLUMN verification_status TEXT NOT NULL DEFAULT 'VERIFIED_PASS'"
                )
            if "chars_per_sec" not in ev_cols:
                con.execute(
                    "ALTER TABLE events ADD COLUMN chars_per_sec REAL NOT NULL DEFAULT 0.0"
                )
            if "domain" not in ev_cols:
                con.execute(
                    "ALTER TABLE events ADD COLUMN domain TEXT NOT NULL DEFAULT 'py:algo'"
                )

            post_cols = {
                r["name"] for r in con.execute("PRAGMA table_info(posteriors)").fetchall()
            }
            if "domain" not in post_cols:
                con.execute(
                    "ALTER TABLE posteriors ADD COLUMN domain TEXT NOT NULL DEFAULT 'py:algo'"
                )

            int_cols = {
                r["name"] for r in con.execute("PRAGMA table_info(interventions)").fetchall()
            }
            if "target_function" not in int_cols:
                con.execute(
                    "ALTER TABLE interventions ADD COLUMN target_function TEXT NOT NULL DEFAULT ''"
                )
            if "domain" not in int_cols:
                con.execute(
                    "ALTER TABLE interventions ADD COLUMN domain TEXT NOT NULL DEFAULT 'py:algo'"
                )
            if "clean_hash" not in int_cols:
                con.execute(
                    "ALTER TABLE interventions ADD COLUMN clean_hash TEXT NOT NULL DEFAULT ''"
                )
            if "clean_code" not in int_cols:
                con.execute(
                    "ALTER TABLE interventions ADD COLUMN clean_code TEXT NOT NULL DEFAULT ''"
                )

    def _compute_global_hyper_mean(self, con: sqlite3.Connection) -> float:
        """Compute weak global hyper-prior mean across all previously observed domains."""
        rows = con.execute(
            """
            SELECT domain, skill_mean
            FROM posteriors
            WHERE id IN (SELECT MAX(id) FROM posteriors GROUP BY domain)
            """
        ).fetchall()
        if not rows:
            return 0.0
        means = [float(r["skill_mean"]) for r in rows]
        return float(HYPER_PRIOR_WEIGHT * np.mean(means))

    def _load_filter(self, con: sqlite3.Connection, domain: str = DEFAULT_DOMAIN) -> tuple[SkillFilter, int]:
        """Load persisted SkillFilter posterior distribution for `domain` from SQLite."""
        dom = str(domain or DEFAULT_DOMAIN)
        post_key = f"filter_post:{dom}"
        sl_key = f"since_last_probe:{dom}"

        row = con.execute(
            "SELECT value FROM thermostat_state WHERE key = ?", (post_key,)
        ).fetchone()
        if row is None and dom == DEFAULT_DOMAIN:
            # Backward-compatibility with legacy unscoped key
            row = con.execute(
                "SELECT value FROM thermostat_state WHERE key = 'filter_post'"
            ).fetchone()

        hyper_mean = self._compute_global_hyper_mean(con) if row is None else 0.0
        filt = SkillFilter(
            1,
            GRID,
            c_grid=C_GRID,
            robust_drift=True,
            prior_mean=hyper_mean,
        )
        if row is not None:
            try:
                arr = np.asarray(json.loads(row["value"]), dtype=float)
                if arr.shape == filt.post.shape:
                    filt.post = arr / arr.sum((1, 2), keepdims=True)
            except (ValueError, KeyError, TypeError):
                pass

        sl_row = con.execute(
            "SELECT value FROM thermostat_state WHERE key = ?", (sl_key,)
        ).fetchone()
        if sl_row is None and dom == DEFAULT_DOMAIN:
            sl_row = con.execute(
                "SELECT value FROM thermostat_state WHERE key = 'since_last_probe'"
            ).fetchone()
        since_last = int(sl_row["value"]) if sl_row is not None else 0
        return filt, since_last

    def _save_filter(
        self, con: sqlite3.Connection, filt: SkillFilter, since_last: int, domain: str = DEFAULT_DOMAIN
    ) -> None:
        dom = str(domain or DEFAULT_DOMAIN)
        post_json = json.dumps(filt.post.tolist())
        con.execute(
            "INSERT OR REPLACE INTO thermostat_state (key, value) VALUES (?, ?)",
            (f"filter_post:{dom}", post_json),
        )
        con.execute(
            "INSERT OR REPLACE INTO thermostat_state (key, value) VALUES (?, ?)",
            (f"since_last_probe:{dom}", str(int(since_last))),
        )
        if dom == DEFAULT_DOMAIN:
            con.execute(
                "INSERT OR REPLACE INTO thermostat_state (key, value) VALUES ('filter_post', ?)",
                (post_json,),
            )
            con.execute(
                "INSERT OR REPLACE INTO thermostat_state (key, value) VALUES ('since_last_probe', ?)",
                (str(int(since_last)),),
            )

    def set_forced_mode(self, mode: str | None) -> None:
        with self._connect() as con:
            if mode is None:
                con.execute("DELETE FROM thermostat_state WHERE key = 'forced_mode'")
            else:
                con.execute(
                    "INSERT OR REPLACE INTO thermostat_state (key, value) VALUES ('forced_mode', ?)",
                    (mode,),
                )

    def get_forced_mode(self) -> str | None:
        with self._connect() as con:
            row = con.execute(
                "SELECT value FROM thermostat_state WHERE key = 'forced_mode'"
            ).fetchone()
            return str(row["value"]) if row else None

    def record_event(
        self,
        repo_hash: str,
        intervention_mode: str,
        prompt_tokens: int,
        completion_tokens: int,
        test_exit_code: int,
        time_to_green_sec: float,
        edit_distance_ratio: float,
        timestamp: float | None = None,
        probe_caught: bool | None = None,
        ast_verified: bool | None = None,
        chars_per_sec: float | None = None,
        verification_status: str | None = None,
        domain: str = DEFAULT_DOMAIN,
        huber_damping: bool = True,
    ) -> dict[str, Any]:
        """Record a real test execution event for `domain` and append an updated Bayesian posterior row."""
        ts = float(timestamp if timestamp is not None else time.time())
        repo_hash = str(repo_hash or "working-tree")
        mode = str(intervention_mode or LEVEL_FULL)
        dom = str(domain or DEFAULT_DOMAIN)
        p_tok = int(prompt_tokens)
        c_tok = int(completion_tokens)
        exit_code = int(test_exit_code)
        ttg = float(max(0.01, time_to_green_sec))
        edit_ratio = float(np.clip(edit_distance_ratio, 0.0, 1.0))
        cps = float(chars_per_sec or 0.0)

        with self._connect() as con:
            filt, since_last = self._load_filter(con, domain=dom)
            ctl = Thermostat(
                ThermostatConfig(
                    floor_probe=self.floor_hat,
                    floor_full=self.floor_full,
                    probe_cadence=self.probe_cadence,
                ),
                GRID,
            )

            yes = np.ones(1, dtype=bool)
            no = np.zeros(1, dtype=bool)

            is_unassisted = mode in (
                LEVEL_SKELETON,
                LEVEL_PROBE_FAULT,
                "UNASSISTED",
                "PROBE",
                "PROBE_UNASSISTED",
            )

            if not is_unassisted:
                filt.predict(wide=yes, learning=no)
                since_last += 1
                if exit_code != 0:
                    filt.update_joint(
                        passed=False,
                        time_to_green_sec=ttg,
                        edit_distance_ratio=edit_ratio,
                        mode=mode,
                        d=-0.2,
                        ast_verified=False,
                        trusted=False,
                        huber_damping=huber_damping,
                    )
                    v_status = verification_status or "ASSISTED_FAIL"
                else:
                    v_status = verification_status or "ASSISTED_PASS"
            else:
                filt.predict(wide=no, learning=yes)
                passed_tests = exit_code == 0
                if ast_verified is None:
                    if probe_caught is False:
                        ast_ok = False
                    elif probe_caught is True:
                        ast_ok = True
                    else:
                        ast_ok = edit_ratio > 0.0
                else:
                    ast_ok = bool(ast_verified)

                if passed_tests and probe_caught is False:
                    ast_ok = False

                filter_status = filt.update_joint(
                    passed=passed_tests,
                    time_to_green_sec=ttg,
                    edit_distance_ratio=edit_ratio,
                    mode=mode,
                    d=0.0,
                    ast_verified=ast_ok,
                    chars_per_sec=cps if cps > 0.0 else None,
                    trusted=(mode == LEVEL_PROBE_FAULT),
                    huber_damping=huber_damping,
                )
                v_status = verification_status or filter_status
                if filter_status in ("UNVERIFIED_PASS", "ANOMALY_PASTE_SUSPECTED"):
                    v_status = filter_status
                    probe_caught = False
                elif probe_caught is None:
                    probe_caught = filter_status.startswith("VERIFIED_PASS")
                since_last = 0

            summ = filt.summary()
            mean_val = float(summ.mean[0])
            std_val = float(summ.sd[0])
            q10_val = float(summ.q10[0])

            controller_level, alpha_val, _ = ctl.decide_hysteresis(
                summ,
                since_last_probe=since_last,
                floor_probe=self.floor_hat,
                floor_full=self.floor_full,
                probe_cadence=self.probe_cadence,
            )

            forced = con.execute(
                "SELECT value FROM thermostat_state WHERE key = 'forced_mode'"
            ).fetchone()
            if forced is not None:
                controller_level = str(forced["value"])

            prev_row = con.execute(
                "SELECT event_hash FROM events ORDER BY id DESC LIMIT 1"
            ).fetchone()
            prev_hash = str(prev_row["event_hash"]) if prev_row and prev_row["event_hash"] else GENESIS_HASH
            canonical_payload = (
                f"{prev_hash}|{ts:.6f}|{repo_hash}|{dom}|{mode}|{p_tok}|{c_tok}|"
                f"{exit_code}|{ttg:.4f}|{edit_ratio:.4f}|{v_status}|{mean_val:.6f}|{std_val:.6f}"
            )
            event_hash = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()

            probe_caught_int = None if probe_caught is None else (1 if probe_caught else 0)
            con.execute(
                """
                INSERT INTO events (
                    timestamp, repo_hash, intervention_mode, prompt_tokens,
                    completion_tokens, test_exit_code, time_to_green_sec,
                    edit_distance_ratio, probe_caught, verification_status,
                    chars_per_sec, domain, event_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ts,
                    repo_hash,
                    mode,
                    p_tok,
                    c_tok,
                    exit_code,
                    ttg,
                    edit_ratio,
                    probe_caught_int,
                    v_status,
                    cps,
                    dom,
                    event_hash,
                ),
            )

            con.execute(
                """
                INSERT INTO posteriors (
                    timestamp, skill_mean, skill_std, controller_level, skill_q10, alpha, domain
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (ts, mean_val, std_val, controller_level, q10_val, alpha_val, dom),
            )

            self._save_filter(con, filt, since_last, domain=dom)

            return {
                "timestamp": ts,
                "repo_hash": repo_hash,
                "domain": dom,
                "intervention_mode": mode,
                "test_exit_code": exit_code,
                "time_to_green_sec": ttg,
                "edit_distance_ratio": edit_ratio,
                "probe_caught": probe_caught,
                "verification_status": v_status,
                "chars_per_sec": cps,
                "event_hash": event_hash,
                "skill_mean": mean_val,
                "skill_std": std_val,
                "skill_q10": q10_val,
                "alpha": alpha_val,
                "controller_level": controller_level,
            }

    def log_intervention(
        self,
        intervention_mode: str,
        transformed_code: str,
        fault_metadata: dict[str, Any] | None = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        target_file: str = "",
        target_function: str = "",
        domain: str = DEFAULT_DOMAIN,
        clean_code: str = "",
        timestamp: float | None = None,
    ) -> dict[str, Any]:
        """Log an AI completion / friction intervention served by the wire proxy or workspace."""
        ts = float(timestamp if timestamp is not None else time.time())
        code_hash = hashlib.sha256(transformed_code.encode("utf-8")).hexdigest()[:16]
        clean_hash = (
            hashlib.sha256(clean_code.encode("utf-8")).hexdigest()[:16]
            if clean_code
            else ""
        )
        meta_json = json.dumps(fault_metadata or {})
        dom = str(domain or DEFAULT_DOMAIN)
        fn_name = str(target_function or (fault_metadata or {}).get("function_name") or "")
        with self._connect() as con:
            con.execute("UPDATE interventions SET resolved = 1 WHERE resolved = 0")
            cur = con.execute(
                """
                INSERT INTO interventions (
                    timestamp, intervention_mode, code_hash, clean_hash,
                    prompt_tokens, completion_tokens, transformed_code, clean_code,
                    fault_metadata_json, target_file, target_function, domain, resolved
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    ts,
                    intervention_mode,
                    code_hash,
                    clean_hash,
                    int(prompt_tokens),
                    int(completion_tokens),
                    transformed_code,
                    clean_code,
                    meta_json,
                    target_file,
                    fn_name,
                    dom,
                ),
            )
            int_id = cur.lastrowid
            if target_file and clean_code:
                snap_payload = json.dumps(
                    {
                        "target_file": target_file,
                        "clean_hash": clean_hash,
                        "clean_code": clean_code,
                        "timestamp": ts,
                    }
                )
                con.execute(
                    "INSERT OR REPLACE INTO thermostat_state (key, value) VALUES (?, ?)",
                    (f"clean_snapshot:{target_file}", snap_payload),
                )
        return {
            "id": int_id,
            "timestamp": ts,
            "intervention_mode": intervention_mode,
            "code_hash": code_hash,
            "clean_hash": clean_hash,
            "prompt_tokens": int(prompt_tokens),
            "completion_tokens": int(completion_tokens),
            "target_file": target_file,
            "target_function": fn_name,
            "domain": dom,
            "fault_metadata": fault_metadata or {},
        }

    def get_clean_snapshot(self, target_file: str) -> dict[str, Any] | None:
        with self._connect() as con:
            row = con.execute(
                "SELECT value FROM thermostat_state WHERE key = ?",
                (f"clean_snapshot:{target_file}",),
            ).fetchone()
            if row is not None:
                try:
                    return json.loads(row["value"])
                except ValueError:
                    pass
            row2 = con.execute(
                "SELECT clean_code, clean_hash FROM interventions WHERE target_file = ? AND clean_code != '' ORDER BY id DESC LIMIT 1",
                (target_file,),
            ).fetchone()
            if row2 is not None:
                return {
                    "target_file": target_file,
                    "clean_code": str(row2["clean_code"]),
                    "clean_hash": str(row2["clean_hash"]),
                }
        return None

    def set_attachment(
        self,
        target_file: str,
        repo_path: str = "",
        domain: str = DEFAULT_DOMAIN,
        test_cmd: str = "",
    ) -> dict[str, Any]:
        payload = {
            "target_file": str(target_file),
            "repo_path": str(repo_path or Path(target_file).resolve().parent),
            "domain": str(domain or DEFAULT_DOMAIN),
            "test_cmd": str(test_cmd or ""),
            "attached_at": time.time(),
        }
        with self._connect() as con:
            con.execute(
                "INSERT OR REPLACE INTO thermostat_state (key, value) VALUES ('attached_target', ?)",
                (json.dumps(payload),),
            )
        return payload

    def get_attachment(self) -> dict[str, Any] | None:
        with self._connect() as con:
            row = con.execute(
                "SELECT value FROM thermostat_state WHERE key = 'attached_target'"
            ).fetchone()
            if row is None:
                return None
            try:
                return json.loads(row["value"])
            except ValueError:
                return None

    def get_active_intervention(self) -> dict[str, Any] | None:
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM interventions WHERE resolved = 0 ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            d = dict(row)
            try:
                d["fault_metadata"] = json.loads(d.get("fault_metadata_json") or "{}")
            except ValueError:
                d["fault_metadata"] = {}
            return d

    def resolve_intervention(self, intervention_id: int) -> None:
        with self._connect() as con:
            con.execute(
                "UPDATE interventions SET resolved = 1 WHERE id = ?",
                (int(intervention_id),),
            )

    def get_latest_posterior(self, domain: str | None = None) -> dict[str, Any]:
        forced = self.get_forced_mode()
        with self._connect() as con:
            if domain:
                row = con.execute(
                    "SELECT * FROM posteriors WHERE domain = ? ORDER BY id DESC LIMIT 1",
                    (str(domain),),
                ).fetchone()
            else:
                row = con.execute(
                    "SELECT * FROM posteriors ORDER BY id DESC LIMIT 1"
                ).fetchone()
            if row is not None:
                d = dict(row)
                if forced is not None:
                    d["controller_level"] = forced
                return d

            dom = str(domain or DEFAULT_DOMAIN)
            filt, _ = self._load_filter(con, domain=dom)
            summ = filt.summary()
            return {
                "id": 0,
                "timestamp": time.time(),
                "domain": dom,
                "skill_mean": float(summ.mean[0]),
                "skill_std": float(summ.sd[0]),
                "skill_q10": float(summ.q10[0]),
                "alpha": 1.0,
                "controller_level": forced or LEVEL_FULL,
            }

    def get_domain_summaries(self) -> list[dict[str, Any]]:
        """Return the latest posterior summary for every tracked domain in `.thermostat.db`."""
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT p.*, (SELECT COUNT(*) FROM events e WHERE e.domain = p.domain) AS event_count
                FROM posteriors p
                WHERE p.id IN (SELECT MAX(id) FROM posteriors GROUP BY domain)
                ORDER BY p.domain ASC
                """
            ).fetchall()
            return [dict(r) for r in rows]

    def get_events(self, limit: int = 100, domain: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as con:
            if domain:
                rows = con.execute(
                    "SELECT * FROM events WHERE domain = ? ORDER BY id ASC LIMIT ?",
                    (str(domain), int(limit)),
                ).fetchall()
            else:
                rows = con.execute(
                    "SELECT * FROM events ORDER BY id ASC LIMIT ?", (int(limit),)
                ).fetchall()
            return [dict(r) for r in rows]

    def get_posteriors(self, limit: int = 100, domain: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as con:
            if domain:
                rows = con.execute(
                    "SELECT * FROM posteriors WHERE domain = ? ORDER BY id ASC LIMIT ?",
                    (str(domain), int(limit)),
                ).fetchall()
            else:
                rows = con.execute(
                    "SELECT * FROM posteriors ORDER BY id ASC LIMIT ?", (int(limit),)
                ).fetchall()
            return [dict(r) for r in rows]

    def get_interventions(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT * FROM interventions ORDER BY id ASC LIMIT ?", (int(limit),)
            ).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                try:
                    d["fault_metadata"] = json.loads(d.get("fault_metadata_json") or "{}")
                except ValueError:
                    d["fault_metadata"] = {}
                out.append(d)
            return out

    def verify_hash_chain(self, records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        """Verify cryptographic SHA-256 hash-chain integrity across events or exported JSONL tuples."""
        if records is None:
            events = self.get_events(limit=5000)
            posts = self.get_posteriors(limit=5000)
            merged: list[dict[str, Any]] = []
            for idx, ev in enumerate(events):
                po = posts[idx] if idx < len(posts) else {}
                item = dict(ev)
                if "skill_mean" not in item:
                    item["skill_mean"] = float(po.get("skill_mean", 0.0))
                if "skill_std" not in item:
                    item["skill_std"] = float(po.get("skill_std", 1.0))
                merged.append(item)
            records = merged

        return verify_event_hash_chain(records)


def verify_event_hash_chain(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Recompute and verify the SHA-256 chain over a sequence of event records."""
    prev_hash = GENESIS_HASH
    checked = 0
    for idx, r in enumerate(records):
        expected_prev = str(r.get("prev_hash") or prev_hash)
        if expected_prev != prev_hash:
            return {
                "verified": False,
                "checked_count": checked,
                "failed_index": idx,
                "reason": f"prev_hash mismatch at index {idx}",
                "chain_head_hash": prev_hash,
            }
        ts = float(r["timestamp"])
        repo_hash = str(r["repo_hash"])
        dom = str(r.get("domain") or DEFAULT_DOMAIN)
        mode = str(r["intervention_mode"])
        p_tok = int(r.get("prompt_tokens", 0))
        c_tok = int(r.get("completion_tokens", 0))
        exit_code = int(r["test_exit_code"])
        ttg = float(r["time_to_green_sec"])
        edit_ratio = float(r["edit_distance_ratio"])
        v_status = str(r.get("verification_status") or "VERIFIED_PASS")
        mean_val = float(r["skill_mean"])
        std_val = float(r["skill_std"])

        canonical_payload = (
            f"{prev_hash}|{ts:.6f}|{repo_hash}|{dom}|{mode}|{p_tok}|{c_tok}|"
            f"{exit_code}|{ttg:.4f}|{edit_ratio:.4f}|{v_status}|{mean_val:.6f}|{std_val:.6f}"
        )
        computed_hash = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()
        recorded_hash = str(r.get("event_hash") or "")
        if recorded_hash and computed_hash != recorded_hash:
            return {
                "verified": False,
                "checked_count": checked,
                "failed_index": idx,
                "reason": f"event_hash mismatch at index {idx}: {computed_hash} != {recorded_hash}",
                "chain_head_hash": prev_hash,
            }
        prev_hash = recorded_hash or computed_hash
        checked += 1

    return {
        "verified": True,
        "checked_count": checked,
        "failed_index": None,
        "reason": "ok",
        "chain_head_hash": prev_hash,
    }
