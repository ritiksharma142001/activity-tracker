"""Background service: every few seconds, record which window is in use."""
import fcntl
import os
import sys
import time

from .db import Database
from .sources import SystemSource

POLL_SECONDS = 5
IDLE_LIMIT_MS = 3 * 60 * 1000  # stop counting after 3 minutes without input


def _lock_path():
    runtime = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
    return os.path.join(runtime, "activity-tracker.lock")


def is_running():
    try:
        with open(_lock_path(), "a") as f:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(f, fcntl.LOCK_UN)
        return False
    except BlockingIOError:
        return True


def run():
    lock = open(_lock_path(), "a")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("activity-tracker daemon is already running", file=sys.stderr)
        return

    db = Database()
    source = SystemSource()
    current_id, current_key = None, None
    last_tick = time.time()

    while True:
        now = time.time()
        # A large gap means the computer was asleep; don't count that time.
        continuous = now - last_tick < POLL_SECONDS * 3
        win = source.focused_window() if source.idle_ms() < IDLE_LIMIT_MS else None
        key = (win["app_id"], win["title"]) if win else None

        if current_id and continuous:
            db.extend_event(current_id, now)
        if key != current_key or not continuous:
            current_id = db.start_event(win["app_id"], win["app_name"], win["title"], now) if win else None
            current_key = key

        last_tick = now
        time.sleep(POLL_SECONDS)
