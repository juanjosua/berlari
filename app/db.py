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
            name TEXT, access_token TEXT, refresh_token TEXT, expires_at INTEGER,
            lang TEXT DEFAULT 'en'           -- UI + coach language
        );
        CREATE TABLE IF NOT EXISTS plans (
            user_id INTEGER PRIMARY KEY REFERENCES users(id),
            params TEXT, stats TEXT, days TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY,          -- Strava activity id
            user_id INTEGER, date TEXT,      -- local date of the run
            km REAL, moving_s INTEGER, avg_hr REAL, data TEXT
        );
        CREATE INDEX IF NOT EXISTS activities_user_date ON activities(user_id, date);
        CREATE TABLE IF NOT EXISTS summaries (
            user_id INTEGER PRIMARY KEY,     -- latest coach fitness summary per user
            date TEXT, text TEXT, n_acts INTEGER, metrics TEXT
        );
        """)
        if "lang" not in [r[1] for r in c.execute("PRAGMA table_info(users)")]:
            c.execute("ALTER TABLE users ADD COLUMN lang TEXT DEFAULT 'en'")  # databases from before i18n


def save_user(uid, name, access, refresh, expires_at) -> None:
    with conn() as c:
        c.execute("INSERT INTO users (id, name, access_token, refresh_token, expires_at) VALUES (?,?,?,?,?) "
                  "ON CONFLICT(id) DO UPDATE SET "
                  "name=excluded.name, access_token=excluded.access_token, "
                  "refresh_token=excluded.refresh_token, expires_at=excluded.expires_at",
                  (uid, name, access, refresh, expires_at))


def set_lang(uid, lang: str) -> None:
    with conn() as c:
        c.execute("UPDATE users SET lang=? WHERE id=?", (lang, uid))


def get_user(uid) -> dict | None:
    with conn() as c:
        row = c.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    return dict(row) if row else None


def save_plan(uid, params: dict, stats: dict, days: list[dict]) -> None:
    with conn() as c:
        c.execute("INSERT OR REPLACE INTO plans (user_id, params, stats, days) VALUES (?,?,?,?)",
                  (uid, json.dumps(params), json.dumps(stats), json.dumps(days)))


def get_plan(uid) -> dict | None:
    with conn() as c:
        row = c.execute("SELECT * FROM plans WHERE user_id=?", (uid,)).fetchone()
    if not row:
        return None
    return {k: json.loads(row[k]) for k in ("params", "stats", "days")}


def save_activity(uid, aid, day: str, run: dict) -> None:
    with conn() as c:
        c.execute("INSERT OR REPLACE INTO activities VALUES (?,?,?,?,?,?,?)",
                  (aid, uid, day, run["km"], round(run["moving_min"] * 60), run.get("avg_hr"), json.dumps(run)))


def delete_activity(uid, aid) -> str | None:
    """Returns the date the activity was on, if we had it."""
    with conn() as c:
        row = c.execute("SELECT date FROM activities WHERE id=? AND user_id=?", (aid, uid)).fetchone()
        c.execute("DELETE FROM activities WHERE id=? AND user_id=?", (aid, uid))
    return row["date"] if row else None


def get_activities(uid, since: str = "") -> list[dict]:
    with conn() as c:
        rows = c.execute("SELECT * FROM activities WHERE user_id=? AND date>=? ORDER BY date, id",
                         (uid, since)).fetchall()
    return [{**dict(r), "data": json.loads(r["data"])} for r in rows]


def get_summary(uid) -> dict | None:
    with conn() as c:
        row = c.execute("SELECT * FROM summaries WHERE user_id=?", (uid,)).fetchone()
    if not row:
        return None
    text = row["text"] or ""
    parts = json.loads(text) if text.startswith("{") else {"headline": "", "better": [], "watch": [], "next": text}
    return {**dict(row), "metrics": json.loads(row["metrics"]), "parts": parts}


def delete_summary(uid) -> None:
    with conn() as c:
        c.execute("DELETE FROM summaries WHERE user_id=?", (uid,))


def save_summary(uid, day: str, text: str, n_acts: int, metrics: dict) -> None:
    with conn() as c:
        c.execute("INSERT OR REPLACE INTO summaries VALUES (?,?,?,?,?)",
                  (uid, day, text, n_acts, json.dumps(metrics)))


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


def athletes() -> list[dict]:
    """Admin overview: every connected athlete with plan and activity info."""
    with conn() as c:
        rows = c.execute("""
            SELECT u.id, u.name, p.params, p.created_at AS plan_created,
                   (SELECT COUNT(*) FROM activities a WHERE a.user_id = u.id) AS runs,
                   (SELECT MAX(date) FROM activities a WHERE a.user_id = u.id) AS last_run,
                   (SELECT date FROM summaries s WHERE s.user_id = u.id) AS summary_date
            FROM users u LEFT JOIN plans p ON p.user_id = u.id ORDER BY u.name""").fetchall()
    return [{**dict(r), "params": json.loads(r["params"]) if r["params"] else None} for r in rows]


def delete_user(uid) -> None:
    with conn() as c:
        c.execute("DELETE FROM plans WHERE user_id=?", (uid,))
        c.execute("DELETE FROM activities WHERE user_id=?", (uid,))
        c.execute("DELETE FROM summaries WHERE user_id=?", (uid,))
        c.execute("DELETE FROM users WHERE id=?", (uid,))
