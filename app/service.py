"""Glue shared by the web routes, the Strava webhook and the nightly job.
Every LLM result is saved; nothing here regenerates text that already exists."""
import json
import logging
from datetime import date, timedelta
from functools import wraps

from . import coach, db, fitness, strava
from . import sessions as S
from .plan import (PHASES, Stats, adapt, adjust_after_failed_phase, build_plan, evaluate_phase, paces,  # noqa: F401
                   plan_to_dicts,
                   plan_phases)

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


def prefs(uid: int) -> dict:
    raw = (db.get_user(uid) or {}).get("prefs")
    return json.loads(raw) if raw else {}


def nutrition(uid: int, saved: dict, day: dict) -> dict | None:
    """Calorie/protein/carb targets and a meal suggestion for one plan day; None until age, height, weight
    and sex are filled in."""
    from . import nutrition as N
    p = prefs(uid)
    if not all(p.get(k) for k in ("age", "height_cm", "weight_kg", "sex")):
        return None
    days_to_race = (date.fromisoformat(saved["params"]["event_date"]) - date.fromisoformat(day["date"])).days
    sess = day.get("sessions") or []
    t = N.targets(p["weight_kg"], p["height_cm"], p["age"], p["sex"], sess, plan_paces(saved)["easy"], days_to_race)
    idx = date.fromisoformat(day["date"]).toordinal()
    weekend = date.fromisoformat(day["date"]).weekday() >= 5
    menu = N.day_meals(idx, sess, t, p.get("rice") or "daily", weekend, p.get("budget"))
    return {"target": t, "menu": menu, "tip": N.TIPS[idx % len(N.TIPS)]}


def bmi(uid: int) -> float | None:
    p = prefs(uid)
    if p.get("height_cm") and p.get("weight_kg"):
        return round(p["weight_kg"] / (p["height_cm"] / 100) ** 2, 1)
    return None


def max_hr_info(uid: int) -> tuple[int | None, str | None]:
    """(max HR, source). Tanaka formula 208 - 0.7 x age when the athlete gave their age (Strava doesn't share
    it); otherwise the highest HR seen in their activities if it looks like a real maximum."""
    age = prefs(uid).get("age")
    if age:
        return round(208 - 0.7 * age), "tanaka"
    seen = max((a["data"].get("max_hr") or 0 for a in db.get_activities(uid)), default=0)
    return (round(seen), "observed") if seen >= 150 else (None, None)


def max_hr(uid: int) -> float:
    return max_hr_info(uid)[0] or 190  # checks need a number; 190 only when nothing is known


def rebuild_plan(uid: int) -> bool:
    """Regenerate the plan from today with the current profile (age, height, weight, default variations) and
    fresh Strava stats, for the same race. Past days stay as they were (with their checks, reviews and
    checkpoint results); variations picked by hand and run reviews on upcoming days are carried over."""
    saved, user = db.get_plan(uid), db.get_user(uid)
    if not saved or not user or saved["params"].get("source") == "custom":
        return False
    p, t = saved["params"], today().isoformat()
    if p["event_date"] <= t:
        return False
    try:
        runs = strava.recent_runs(user)
        seed_activities(uid, runs)
        stats = strava.stats_from_runs(runs)
    except Exception:  # Strava down: rebuild from the stats we already have
        log.exception("rebuild: Strava fetch failed for %s", uid)
        stats = Stats(**saved["stats"])
    g = (p.get("goal_time") or "").split(":")
    goal_s = int(g[0]) * 3600 + int(g[1]) * 60 if len(g) == 2 and all(x.isdigit() for x in g) else None
    new_days = plan_to_dicts(build_plan(stats, p["distance"], date.fromisoformat(p["event_date"]),
                                        p.get("runs_per_week") or 4, goal_s, prefs=prefs(uid).get("var"), bmi=bmi(uid)))
    old = {d["date"]: d for d in saved["days"]}
    for d in new_days:
        prev = old.get(d["date"]) or {}
        if prev.get("review"):
            d["review"] = prev["review"]
        picked = {x["type"]: x["var"] for x in prev.get("sessions") or [] if x.get("var_set")}
        for x in d["sessions"]:
            if x["type"] in picked:
                x["var"], x["var_set"] = picked[x["type"]], True
    past = [d for d in saved["days"] if d["date"] < t]
    db.save_plan(uid, p, stats.__dict__, past + [d for d in new_days if d["date"] >= t])
    return True


def save_prefs(uid: int, new: dict) -> None:
    """Save age + default variations, and re-apply defaults to upcoming sessions the athlete didn't pick by hand."""
    db.set_prefs(uid, new)
    defaults = new.get("var") or {}

    def apply(by_date):
        for k, d in by_date.items():
            if k < today().isoformat():
                continue
            touched = False
            for x in d.get("sessions") or []:
                fam = S.FAMILY.get(x["type"])
                if fam and not x.get("var_set") and (defaults.get(fam) or x.get("rec")):
                    want = defaults.get(fam) or x.get("rec")
                    if x.get("var") != want:
                        x["var"], touched = want, True
            if touched:
                d.pop("why", None)
    db.update_days(uid, apply)


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
        if d and day >= today().isoformat() and 0 <= idx < len(sess) and var in [v["id"] for v in S.variations(sess[idx])]:
            sess[idx]["var"], sess[idx]["var_set"] = var, True
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


def evaluate_phases(uid: int) -> list[dict]:
    """Nightly: on (or after) a phase's checkpoint day, judge the phase. If the goal wasn't reached, make the
    next phase lighter. The result is stored on the checkpoint day and shown on the plan page."""
    saved = db.get_plan(uid)
    if not saved or saved["params"].get("source") == "custom":
        return []
    days = days_with_runs(uid, saved)
    by_date = {d["date"]: d for d in days}
    phases, t, done = plan_phases(days), today().isoformat(), []
    for i, ph in enumerate(phases):
        cp = by_date.get(ph["checkpoint"] or "")
        if not cp or cp.get("checkpoint_result"):
            continue
        long_state = next((c.get("state") for x, c in zip(cp["sessions"], cp["checks"]) if x["type"] == "LONG"), None)
        if not (ph["checkpoint"] < t or (ph["checkpoint"] == t and long_state == "done")):
            continue
        res = evaluate_phase(ph, days)
        nxt = phases[i + 1] if i + 1 < len(phases) else None
        res["phase"], res["next"] = ph["key"], nxt["key"] if nxt else None
        res["adjusted"] = 0
        if not res["passed"] and nxt and nxt["key"] in ("build1", "build2", "peak"):
            box = []
            db.update_days(uid, lambda bd: box.append(adjust_after_failed_phase(bd, nxt["key"], ph["checkpoint"])))
            res["adjusted"] = box[0] if box else 0
        db.update_days(uid, lambda bd: bd[ph["checkpoint"]].__setitem__("checkpoint_result", res))
        done.append(res)
    return done


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
