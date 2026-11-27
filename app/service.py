"""Glue shared by the web routes, the Strava webhook and the nightly job.
Every LLM result is saved; nothing here regenerates text that already exists."""
import json
import logging
from datetime import date, timedelta
from functools import wraps

from . import coach, db, fitness, strava
from . import sessions as S
from .plan import Stats, adapt, paces

log = logging.getLogger("berlari")
_busy: set[tuple[str, int]] = set()  # (task, user) running now: page refreshes don't stack LLM calls


def today() -> date:
    return date.today()  # server runs with TZ=Asia/Jakarta (deploy/berlari.service)


def user_lang(uid: int) -> str:
    return (db.get_user(uid) or {}).get("lang") or "en"


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


def max_hr(uid: int) -> float:
    """Highest heart rate seen in the athlete's activities (for 'hard effort' checks); 190 if none."""
    return max((a["data"].get("max_hr") or 0 for a in db.get_activities(uid)), default=0) or 190


def days_with_runs(uid: int, saved: dict) -> list[dict]:
    """Plan days with that day's Strava activities, a check per planned session and a day status."""
    first = saved["days"][0]["date"] if saved["days"] else ""
    streams = db.get_streams(uid, first)
    runs: dict[str, list[dict]] = {}
    for a in db.get_activities(uid, first):
        runs.setdefault(a["date"], []).append(a["data"] | {"id": a["id"], "stream": streams.get(a["id"])})
    t, mhr, pc = today().isoformat(), max_hr(uid), plan_paces(saved)
    out = []
    for d in saved["days"]:
        acts, past = runs.get(d["date"], []), d["date"] < t
        sess = d.get("sessions") or S.from_legacy(d)
        checks = [S.check(s, acts, past, mhr, pc) for s in sess]
        out.append(d | {"runs": acts, "sessions": sess, "checks": checks,
                        "status": S.day_state(checks, acts, sess, past)})
    return out


def plan_paces(saved: dict) -> dict:
    """Easy/tempo/interval/race paces (s/km) the plan uses, for pace-based variation checks."""
    g = (saved["params"].get("goal_time") or "").split(":")
    goal_s = int(g[0]) * 3600 + int(g[1]) * 60 if len(g) == 2 and all(x.isdigit() for x in g) else None
    return paces(Stats(**saved["stats"]), saved["params"]["distance"], goal_s)


def set_variation(uid: int, day: str, idx: int, var: str) -> bool:
    """Athlete picked another variation for an upcoming session. Its coach note is rewritten."""
    ok = []

    def apply(by_date):
        d = by_date.get(day)
        sess = (d or {}).get("sessions") or []
        if d and day >= today().isoformat() and 0 <= idx < len(sess) and var in [v[0] for v in S.variations(sess[idx])]:
            sess[idx]["var"] = var
            d.pop("why", None)
            ok.append(True)
    db.update_days(uid, apply)
    return bool(ok)


def current_metrics(uid: int, saved: dict) -> dict:
    return fitness.metrics(db.get_activities(uid), threshold_pace(saved["stats"]), today())


def context(uid: int, saved: dict) -> dict:
    """What the coach gets to know: last 7 days planned vs actual, plus fitness numbers."""
    t = today()
    lo = (t - timedelta(days=7)).isoformat()
    recent = [{"date": d["date"], "planned": d["detail"], "status": d["status"], "actual": d["runs"]}
              for d in days_with_runs(uid, saved) if lo <= d["date"] < t.isoformat()]
    return {"last_7_days": recent, "metrics": current_metrics(uid, saved),
            "runner": saved["stats"], "target": target(saved)}


def target(saved: dict) -> dict:
    return saved["params"] | {"days_to_race": (date.fromisoformat(saved["params"]["event_date"]) - today()).days}


def adapt_plan(uid: int) -> list[str]:
    """Nightly, before tomorrow's notes: reshape upcoming days after missed/short runs (rules in plan.adapt)."""
    saved = db.get_plan(uid)
    if not saved or saved["params"].get("source") == "custom":  # imported plans are followed as written
        return []
    acts = db.get_activities(uid)
    km_by_date: dict[str, float] = {}
    for a in acts:
        km_by_date[a["date"]] = km_by_date.get(a["date"], 0) + a["km"]
    form = fitness.metrics(acts, threshold_pace(saved["stats"]), today() + timedelta(days=1))["today"]["form"]
    changes: list[str] = []
    db.update_days(uid, lambda by_date: changes.extend(adapt(by_date, km_by_date, today().isoformat(), form)))
    if changes:
        log.warning("plan adjusted for user %s: %s", uid, changes)
    return changes


def change_language(uid: int, lang: str) -> bool:
    """Save the language; if it changed, drop today/tomorrow's notes and the summary so they get
    rewritten in the new language (2 LLM calls). Older notes and run reviews stay as written."""
    if user_lang(uid) == lang:
        return False
    db.set_lang(uid, lang)
    soon = {today().isoformat(), (today() + timedelta(days=1)).isoformat()}
    db.update_days(uid, lambda by_date: [by_date[k].pop("why", None) for k in soon if k in by_date])
    db.delete_summary(uid)
    return True


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
    why = coach.explain_days(todo, context(uid, saved), user_lang(uid))

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
    parts = coach.daily_summary(m, recent, target(saved), prev["text"] if prev else None, user_lang(uid))
    db.save_summary(uid, today().isoformat(), json.dumps(parts), len(acts), m)


def recent_runs(uid: int, n: int = 200) -> list[dict]:  # newest first; card scrolls
    return [a["data"] | {"id": a["id"], "date": a["date"]} for a in db.get_activities(uid)[-n:]][::-1]


def chart(uid: int, saved: dict) -> dict:
    """Fitness and fatigue over the last 6 weeks as SVG polyline points."""
    s = fitness.series(db.get_activities(uid), threshold_pace(saved["stats"]), today())
    days = [(today() - timedelta(days=i)).isoformat() for i in range(41, -1, -1)]
    fit = [s.get(d, {}).get("fitness", 0) for d in days]
    fat = [s.get(d, {}).get("fatigue", 0) for d in days]
    top = max(fit + fat + [1])
    return {"fit": fitness.spark(fit, top), "fat": fitness.spark(fat, top)}


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
    text = coach.review_session(d, actual, context(uid, saved), user_lang(uid))
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
    kind = a.get("sport_type", a.get("type"))
    if kind not in S.ACTIVITY_TYPES:
        _drop_review_if_no_runs(uid, db.delete_activity(uid, aid))  # e.g. changed to a ride
        return
    day_key = a["start_date_local"][:10]
    stream = None
    if kind in S.RUN_TYPES:
        try:
            stream = strava.run_stream(user, aid)
        except Exception:  # keep the run even if the detailed stream isn't available
            log.exception("stream fetch failed for activity %s", aid)
    db.save_activity(uid, aid, day_key, strava.run_summary(a), stream)
    if kind not in S.STRENGTH_TYPES:
        review_day(uid, day_key)
