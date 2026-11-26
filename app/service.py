"""Glue shared by the web routes, the Strava webhook and the nightly job.
Every LLM result is saved; nothing here regenerates text that already exists."""
import logging
from datetime import date, timedelta
from functools import wraps

from . import coach, db, fitness, strava
from .plan import day_status

log = logging.getLogger("berlari")
_busy: set[tuple[str, int]] = set()  # (task, user) running now: page refreshes don't stack LLM calls


def today() -> date:
    return date.today()  # server runs with TZ=Asia/Jakarta (deploy/berlari.service)


def threshold_pace(stats: dict) -> float:
    return stats["easy_pace_s"] - 50  # same tempo pace plan.paces() uses


def coach_task(fn):
    """Skip if the coach is off or the same task already runs for this user; log instead of raising."""
    @wraps(fn)
    def wrapper(uid, *args, **kwargs):
        key = (fn.__name__, uid)
        if not coach.enabled() or key in _busy:
            return
        _busy.add(key)
        try:
            return fn(uid, *args, **kwargs)
        except Exception:
            log.exception("%s failed for user %s", fn.__name__, uid)
        finally:
            _busy.discard(key)
    return wrapper


def seed_activities(uid: int, runs: list[dict]) -> None:
    for a in runs:
        db.save_activity(uid, a["id"], a["start_date_local"][:10], strava.run_summary(a))


def days_with_runs(uid: int, saved: dict) -> list[dict]:
    """Plan days with that day's Strava runs and a done/partial/missed status attached."""
    first = saved["days"][0]["date"] if saved["days"] else ""
    runs: dict[str, list[dict]] = {}
    for a in db.get_activities(uid, first):
        runs.setdefault(a["date"], []).append(a["data"])
    t = today().isoformat()
    out = []
    for d in saved["days"]:
        d = d | {"runs": runs.get(d["date"], [])}
        d["status"] = day_status(d, t)
        out.append(d)
    return out


def current_metrics(uid: int, saved: dict) -> dict:
    return fitness.metrics(db.get_activities(uid), threshold_pace(saved["stats"]), today())


def context(uid: int, saved: dict) -> dict:
    """What the coach gets to know: last 7 days planned vs actual, plus fitness numbers."""
    t = today()
    lo = (t - timedelta(days=7)).isoformat()
    recent = [{"date": d["date"], "planned": f"{d['kind']} {d['km']} km", "status": d["status"], "actual": d["runs"]}
              for d in days_with_runs(uid, saved) if lo <= d["date"] < t.isoformat()]
    return {"last_7_days": recent, "metrics": current_metrics(uid, saved),
            "runner": saved["stats"], "target": target(saved)}


def target(saved: dict) -> dict:
    return saved["params"] | {"days_to_race": (date.fromisoformat(saved["params"]["event_date"]) - today()).days}


@coach_task
def ensure_notes(uid: int) -> None:
    """Coach note for today and tomorrow. Normally written the evening before by the nightly job;
    written at most once per day, so refreshing the page never calls the LLM again."""
    saved = db.get_plan(uid)
    if not saved:
        return
    keys = {today().isoformat(), (today() + timedelta(days=1)).isoformat()}
    todo = [d for d in saved["days"] if d["date"] in keys and not d.get("why")]
    if not todo:
        return
    why = coach.explain_days(todo, context(uid, saved))

    def apply(by_date):
        for k, text in why.items():
            if k in by_date and k in keys:
                by_date[k]["why"] = text
    db.update_days(uid, apply)


@coach_task
def refresh_summary(uid: int, force: bool = False) -> None:
    """Fitness summary: at most once a day, and only when runs changed since the last one
    (force=True when a new plan is created, since the target changed)."""
    saved = db.get_plan(uid)
    if not saved:
        return
    acts = db.get_activities(uid)
    prev = db.get_summary(uid)
    if prev and not force and (prev["date"] == today().isoformat() or prev["n_acts"] == len(acts)):
        return
    m = fitness.metrics(acts, threshold_pace(saved["stats"]), today())
    week_ago = (today() - timedelta(days=7)).isoformat()
    recent = [a["data"] | {"date": a["date"]} for a in acts if a["date"] >= week_ago]
    text = coach.daily_summary(m, recent, target(saved), prev["text"] if prev else None)
    db.save_summary(uid, today().isoformat(), text, len(acts), m)


@coach_task
def review_day(uid: int, day_key: str) -> None:
    """Post-run review, once per day (edits to the activity don't re-run it)."""
    saved = db.get_plan(uid)
    if not saved:
        return
    d = next((x for x in days_with_runs(uid, saved) if x["date"] == day_key), None)
    if not d or d.get("review") or not d["runs"]:
        return
    actual = {"runs": d["runs"], "total_km": round(sum(r["km"] for r in d["runs"]), 2)}
    text = coach.review_session(d, actual, context(uid, saved))
    db.update_days(uid, lambda by_date: by_date[day_key].__setitem__("review", text))


# --- Strava webhook events: https://developers.strava.com/docs/webhooks/ ---

def handle_event(ev: dict) -> None:
    try:
        _handle_event(ev)
    except Exception:
        log.exception("webhook event failed: %s", ev)


def _drop_review_if_no_runs(uid: int, day_key: str | None) -> None:
    if day_key and not [a for a in db.get_activities(uid, day_key) if a["date"] == day_key]:
        db.update_days(uid, lambda by_date: by_date.get(day_key, {}).pop("review", None))


def _handle_event(ev: dict) -> None:
    uid = ev.get("owner_id")
    if ev.get("object_type") == "athlete":
        if str(ev.get("updates", {}).get("authorized")) == "false":
            db.delete_user(uid)  # user revoked access on Strava: forget them
        return
    user = db.get_user(uid)
    if ev.get("object_type") != "activity" or not user:
        return
    aid = int(ev["object_id"])
    if ev.get("aspect_type") == "delete":
        _drop_review_if_no_runs(uid, db.delete_activity(uid, aid))
        return
    a = strava.get_activity(user, aid)
    if a.get("sport_type", a.get("type")) not in strava.RUN_TYPES:
        _drop_review_if_no_runs(uid, db.delete_activity(uid, aid))  # e.g. changed from Run to Walk
        return
    day_key = a["start_date_local"][:10]
    db.save_activity(uid, aid, day_key, strava.run_summary(a))
    review_day(uid, day_key)
