import json
import os
import sqlite3
from contextlib import contextmanager

PATH = os.environ.get("BERLARI_DB", "berlari.db")


@contextmanager
def conn():
    """Commit on success, roll back on error, always close (sqlite3's own `with` never closes)."""
    c = sqlite3.connect(PATH)
    c.row_factory = sqlite3.Row
    try:
        with c:
            yield c
    finally:
        c.close()


def init() -> None:
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,          -- Strava athlete id
            name TEXT, access_token TEXT, refresh_token TEXT, expires_at INTEGER
        );
        CREATE TABLE IF NOT EXISTS plans (
            user_id INTEGER PRIMARY KEY REFERENCES users(id),
            params TEXT, stats TEXT, days TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            summary TEXT
        );
        """)
        if "summary" not in [r[1] for r in c.execute("PRAGMA table_info(plans)")]:
            c.execute("ALTER TABLE plans ADD COLUMN summary TEXT")  # pre-coach databases


def save_user(uid, name, access, refresh, expires_at) -> None:
    with conn() as c:
        c.execute("INSERT INTO users VALUES (?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET "
                  "name=excluded.name, access_token=excluded.access_token, "
                  "refresh_token=excluded.refresh_token, expires_at=excluded.expires_at",
                  (uid, name, access, refresh, expires_at))


def get_user(uid) -> dict | None:
    with conn() as c:
        row = c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    return dict(row) if row else None


def save_plan(uid, params: dict, stats: dict, days: list[dict]) -> None:
    with conn() as c:
        c.execute("INSERT OR REPLACE INTO plans (user_id, params, stats, days, summary) VALUES (?,?,?,?,NULL)",
                  (uid, json.dumps(params), json.dumps(stats), json.dumps(days)))


def get_plan(uid) -> dict | None:
    with conn() as c:
        row = c.execute("SELECT * FROM plans WHERE user_id=?", (uid,)).fetchone()
    if not row:
        return None
    return {**{k: json.loads(row[k]) for k in ("params", "stats", "days")}, "summary": row["summary"]}


def set_summary(uid, text: str) -> None:
    with conn() as c:
        c.execute("UPDATE plans SET summary=? WHERE user_id=?", (text, uid))


def update_days(uid, fn) -> None:
    """Atomic read-modify-write of a plan's days: fn(days_by_date) mutates in place.
    BEGIN IMMEDIATE serialises concurrent background tasks so updates don't overwrite each other."""
    c = sqlite3.connect(PATH, isolation_level=None)
    try:
        c.execute("BEGIN IMMEDIATE")
        row = c.execute("SELECT days FROM plans WHERE user_id=?", (uid,)).fetchone()
        if row:
            days = json.loads(row[0])
            fn({d["date"]: d for d in days})
            c.execute("UPDATE plans SET days=? WHERE user_id=?", (json.dumps(days), uid))
        c.execute("COMMIT")
    except BaseException:
        if c.in_transaction:
            c.execute("ROLLBACK")
        raise
    finally:
        c.close()


def delete_user(uid) -> None:
    with conn() as c:
        c.execute("DELETE FROM plans WHERE user_id=?", (uid,))
        c.execute("DELETE FROM users WHERE id=?", (uid,))
