"""SQLite storage. Each row is one continuous stretch of time in one window."""
import os
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id       INTEGER PRIMARY KEY,
    app_id   TEXT NOT NULL,
    app_name TEXT NOT NULL,
    title    TEXT NOT NULL,
    start    REAL NOT NULL,
    end      REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_start ON events(start);
"""


def default_path():
    data_home = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(data_home, "activity-tracker", "activity.db")


class Database:
    def __init__(self, path=None):
        path = path or default_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.conn = sqlite3.connect(path, timeout=5)
        # WAL lets the UI read while the daemon writes.
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)

    def start_event(self, app_id, app_name, title, ts):
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO events (app_id, app_name, title, start, end) VALUES (?, ?, ?, ?, ?)",
                (app_id, app_name, title, ts, ts),
            )
        return cur.lastrowid

    def extend_event(self, event_id, ts):
        with self.conn:
            self.conn.execute("UPDATE events SET end = ? WHERE id = ?", (ts, event_id))

    def usage_by_app(self, t0, t1):
        """[(app_id, app_name, seconds)] for time between t0 and t1, biggest first."""
        return self.conn.execute(
            """SELECT app_id, MAX(app_name), SUM(MIN(end, :t1) - MAX(start, :t0)) AS secs
               FROM events WHERE end > :t0 AND start < :t1
               GROUP BY app_id ORDER BY secs DESC""",
            {"t0": t0, "t1": t1},
        ).fetchall()

    def top_titles(self, app_id, t0, t1, limit=8):
        """[(title, seconds)] for one app."""
        return self.conn.execute(
            """SELECT title, SUM(MIN(end, :t1) - MAX(start, :t0)) AS secs
               FROM events WHERE app_id = :app AND end > :t0 AND start < :t1
               GROUP BY title ORDER BY secs DESC LIMIT :limit""",
            {"app": app_id, "t0": t0, "t1": t1, "limit": limit},
        ).fetchall()
