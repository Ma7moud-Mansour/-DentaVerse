import json
import sqlite3
from pathlib import Path

PROFILES = {
    "guest": {"id": "guest", "name": "Guest workspace", "level": "beginner"},
    "DV-STUDENT-01": {"id": "DV-STUDENT-01", "name": "Beginning learner", "level": "beginner"},
    "DV-STUDENT-02": {"id": "DV-STUDENT-02", "name": "Experienced learner", "level": "experienced"},
    "DV-TEACHER-01": {"id": "DV-TEACHER-01", "name": "Teaching demonstrator", "level": "demonstrator"},
}


class Store:
    def __init__(self, path: str | Path):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY, user_id TEXT NOT NULL, saved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            note TEXT NOT NULL, data TEXT NOT NULL)""")
        self.db.execute("CREATE INDEX IF NOT EXISTS sessions_user ON sessions(user_id)")
        self.db.execute("CREATE TABLE IF NOT EXISTS workspace (id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL)")
        self.db.commit()

    def save(self, session: dict, user_id: str, note: str) -> None:
        existing = self.db.execute("SELECT user_id FROM sessions WHERE id=?", (session["id"],)).fetchone()
        if existing and existing["user_id"] != user_id:
            raise ValueError("Session ownership mismatch")
        self.db.execute("""INSERT INTO sessions(id,user_id,note,data) VALUES(?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET note=excluded.note,data=excluded.data,saved_at=CURRENT_TIMESTAMP""",
            (session["id"], user_id, note, json.dumps(session, allow_nan=False)))
        self.db.commit()

    def journal(self, user_id: str) -> list[dict]:
        rows = self.db.execute("SELECT id,saved_at,note,data FROM sessions WHERE user_id=? ORDER BY saved_at DESC,id DESC LIMIT 100", (user_id,))
        return [{**dict(row), "data": json.loads(row["data"])} for row in rows]

    def close(self):
        self.db.close()

    def save_workspace(self, profile_id: str, session: dict, hand: str = "right") -> None:
        # Only resumable learning state is stored. Never persist camera landmarks,
        # worker connections, calibration or Bluetooth discovery results.
        data = json.dumps({"version": 1, "profile_id": profile_id, "session": session, "hand": hand}, allow_nan=False)
        self.db.execute("INSERT INTO workspace(id,data) VALUES(1,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data", (data,))
        self.db.commit()

    def load_workspace(self) -> dict | None:
        row = self.db.execute("SELECT data FROM workspace WHERE id=1").fetchone()
        if row is None:
            return None
        try:
            data = json.loads(row["data"])
            return data if isinstance(data, dict) else None
        except (ValueError, TypeError):
            return None
