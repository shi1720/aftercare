import json
import hashlib
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone

from .evidence import canonical, event_hash
from contextlib import contextmanager
from pathlib import Path


class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "aftercare.sqlite3"
        self.lock = threading.RLock()
        with self.connection() as conn:
            conn.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,name TEXT NOT NULL,email TEXT UNIQUE,password TEXT,demo INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id TEXT NOT NULL,expires REAL NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id));
                CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,user_id TEXT NOT NULL,body TEXT NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id));
                CREATE TABLE IF NOT EXISTS rate_limits(key TEXT PRIMARY KEY,count INTEGER NOT NULL,window REAL NOT NULL);
            """)
            if "sealed_sha256" not in {row["name"] for row in conn.execute("PRAGMA table_info(runs)")}:
                conn.execute("ALTER TABLE runs ADD COLUMN sealed_sha256 TEXT")
            # A process crash must never leave an apparently progressing release.
            for row in conn.execute("SELECT id,body FROM runs").fetchall():
                run = json.loads(row["body"])
                if run["status"] == "running":
                    run["status"] = "failed"
                    run["completedAt"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                    run["stage"] = "govern"
                    run["decision"] = {"outcome": "stopped", "reason": "Controller restarted. Incomplete sandbox work stopped; start a new isolated recovery."}
                    run["after"]["healthStatus"] = "unverified"
                    run["after"]["contractStatus"] = "unverified"
                    folder = self.root / "runs" / run["id"]
                    if (folder / "safe.py").is_file():
                        safe_digest = hashlib.sha256((folder / "safe.py").read_bytes()).hexdigest()
                        (folder / "active-revision.json").write_text(json.dumps({"revision": safe_digest, "source": "safe.py"}))
                        run["after"] = {"revision": safe_digest[:12], "healthStatus": "safe-revision-retained", "contractStatus": "unverified"}
                    event = {"id": str(uuid.uuid4()), "at": run["completedAt"], "stage": "govern", "title": "Interrupted work stopped", "detail": run["decision"]["reason"], "kind": "error", "previousHash": run["events"][-1]["hash"] if run["events"] else "0"*64}
                    event["hash"] = event_hash(event)
                    run["events"].append(event)
                    for stage in run["stages"]:
                        if stage["id"] == "govern":
                            stage.update(status="failed", detail="Controller restarted before completion")
                        elif stage["status"] in ("running", "pending"):
                            stage.update(status="blocked", detail="Controller restarted before completion")
                    conn.execute("UPDATE runs SET body=?,sealed_sha256=? WHERE id=?", (json.dumps(run), hashlib.sha256(canonical(run)).hexdigest(), row["id"]))
        os.chmod(self.path, 0o600)

    @contextmanager
    def connection(self):
        with self.lock:
            conn = sqlite3.connect(str(self.path), timeout=15)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def save_run(self, user_id, run):
        with self.connection() as conn:
            existing = conn.execute("SELECT user_id,sealed_sha256 FROM runs WHERE id=?", (run["id"],)).fetchone()
            if existing and existing["user_id"] != user_id:
                raise ValueError("Run owner mismatch")
            if existing and existing["sealed_sha256"]:
                if existing["sealed_sha256"] != hashlib.sha256(canonical(run)).hexdigest():
                    raise ValueError("Completed run seal is immutable")
                return
            conn.execute("INSERT INTO runs(id,user_id,body) VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body", (run["id"], user_id, json.dumps(run)))

    def seal_run(self, user_id, run):
        if run["status"] == "running" or not run.get("completedAt"):
            raise ValueError("Only completed runs can be sealed")
        seal = hashlib.sha256(canonical(run)).hexdigest()
        with self.connection() as conn:
            row = conn.execute("SELECT user_id,sealed_sha256 FROM runs WHERE id=?", (run["id"],)).fetchone()
            if not row or row["user_id"] != user_id:
                raise ValueError("Run owner mismatch")
            if row["sealed_sha256"] and row["sealed_sha256"] != seal:
                raise ValueError("Completed run seal is immutable")
            conn.execute("UPDATE runs SET body=?,sealed_sha256=? WHERE id=?", (json.dumps(run), seal, run["id"]))

    def seal_matches(self, user_id, run):
        with self.connection() as conn:
            row = conn.execute("SELECT sealed_sha256 FROM runs WHERE id=? AND user_id=?", (run["id"], user_id)).fetchone()
            return bool(row and row["sealed_sha256"] and row["sealed_sha256"] == hashlib.sha256(canonical(run)).hexdigest())

    def run(self, user_id, run_id):
        with self.connection() as conn:
            row = conn.execute("SELECT body FROM runs WHERE id=? AND user_id=?", (run_id, user_id)).fetchone()
            return json.loads(row["body"]) if row else None

    def runs(self, user_id):
        with self.connection() as conn:
            return [json.loads(row["body"]) for row in conn.execute("SELECT body FROM runs WHERE user_id=? ORDER BY rowid DESC LIMIT 100", (user_id,))]

    def health(self):
        with self.connection() as conn:
            conn.execute("SELECT 1").fetchone()

    def create_user(self, user_id, name, email, password=None, demo=False):
        with self.connection() as conn:
            conn.execute("INSERT INTO users(id,name,email,password,demo) VALUES(?,?,?,?,?)", (user_id, name, email, password, int(demo)))

    def user_by_email(self, email):
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
            return dict(row) if row else None

    def session_user(self, hashed_token, current):
        with self.connection() as conn:
            row = conn.execute("SELECT users.* FROM users JOIN sessions ON users.id=sessions.user_id WHERE sessions.token=? AND expires>?", (hashed_token, current)).fetchone()
            return dict(row) if row else None

    def put_session(self, hashed_token, user_id, expires, previous=None):
        import time
        with self.connection() as conn:
            if previous:
                conn.execute("DELETE FROM sessions WHERE token=?", (previous,))
            conn.execute("DELETE FROM sessions WHERE expires<=?", (time.time(),))
            conn.execute("INSERT INTO sessions(token,user_id,expires) VALUES(?,?,?)", (hashed_token, user_id, expires))

    def delete_session(self, hashed_token):
        with self.connection() as conn:
            conn.execute("DELETE FROM sessions WHERE token=?", (hashed_token,))

    def check_rate_limit(self, key, limit, seconds, current):
        with self.connection() as conn:
            row = conn.execute("SELECT count,window FROM rate_limits WHERE key=?", (key,)).fetchone()
            if row and current-row["window"] < seconds:
                if row["count"] >= limit:
                    return False
                conn.execute("UPDATE rate_limits SET count=count+1 WHERE key=?", (key,))
            else:
                conn.execute("INSERT INTO rate_limits(key,count,window) VALUES(?,1,?) ON CONFLICT(key) DO UPDATE SET count=1,window=excluded.window", (key, current))
            conn.execute("DELETE FROM rate_limits WHERE window<?", (current-86400,))
        return True

    def run_count(self, user_id=None):
        with self.connection() as conn:
            if user_id:
                return conn.execute("SELECT COUNT(*) FROM runs WHERE user_id=?", (user_id,)).fetchone()[0]
            return conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]

    def put_artifact(self, run_id, name, data):
        # Local artifacts already live alongside their execution directory.
        pass

    def get_artifact(self, run_id, name):
        path = self.root / "runs" / run_id / name
        return path.read_bytes() if path.is_file() else None
