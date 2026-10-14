"""SQLite event log. Everything the study needs is an event; participant state is rebuilt by replaying them."""
import json
import sqlite3
import threading
import time


class Store:
    def __init__(self, path=":memory:"):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.Lock()
        with self.lock:
            self.db.executescript("""
                CREATE TABLE IF NOT EXISTS participants (pid TEXT PRIMARY KEY, name TEXT, seed INTEGER, ts REAL);
                CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, pid TEXT, ts REAL,
                                                   kind TEXT, payload TEXT);
                CREATE INDEX IF NOT EXISTS ev_pid ON events(pid, id);
            """)
            self.db.commit()

    def add_participant(self, pid, name, seed):
        with self.lock:
            self.db.execute("INSERT INTO participants VALUES (?,?,?,?)", (pid, name, seed, time.time()))
            self.db.commit()

    def participant(self, pid):
        with self.lock:
            return self.db.execute("SELECT pid, name, seed FROM participants WHERE pid=?", (pid,)).fetchone()

    def add_event(self, pid, kind, payload):
        with self.lock:
            self.db.execute("INSERT INTO events (pid, ts, kind, payload) VALUES (?,?,?,?)",
                            (pid, time.time(), kind, json.dumps(payload)))
            self.db.commit()

    def events(self, pid):
        with self.lock:
            rows = self.db.execute("SELECT ts, kind, payload FROM events WHERE pid=? ORDER BY id", (pid,)).fetchall()
        return [(ts, kind, json.loads(p)) for ts, kind, p in rows]

    def export(self):
        with self.lock:
            parts = self.db.execute("SELECT pid, name, seed, ts FROM participants").fetchall()
        return [dict(pid=p, name=n, seed=s, ts=t,
                     events=[dict(ts=ts, kind=k, **pl) for ts, k, pl in self.events(p)]) for p, n, s, t in parts]
