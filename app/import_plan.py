"""Load a custom, hand-written plan for one athlete (replaces their current plan):
    python -m app.import_plan <strava_athlete_id> <plan.json>
Format: see examples/bfi-run-2027-half-marathon.json and the session fields in app/sessions.py.
Custom plans are followed as written: the nightly auto-adjust rules leave them alone."""
import json
import sys
from datetime import date

from dotenv import load_dotenv

load_dotenv()

from . import db, service  # noqa: E402
from .plan import DISTANCES_KM, make_day, plan_to_dicts  # noqa: E402
from .sessions import LABELS  # noqa: E402

DEFAULT_STATS = {"weekly_km": 10.0, "longest_km": 5.0, "easy_pace_s": 420.0}


def load(uid: int, data: dict) -> int:
    if not db.get_user(uid):
        raise ValueError(f"athlete {uid} has never connected to Berlari")
    date.fromisoformat(data["event_date"])
    if data["distance"] not in DISTANCES_KM:
        raise ValueError(f"distance must be one of {list(DISTANCES_KM)}")
    for d in data["days"]:
        date.fromisoformat(d["date"])
        bad = [s.get("type") for s in d["sessions"] if s.get("type") not in LABELS]
        if not d["sessions"] or bad:
            raise ValueError(f"{d['date']}: unknown or missing session type {bad}")
    days = [make_day(d["date"], d["sessions"]) for d in sorted(data["days"], key=lambda d: d["date"])]
    old = db.get_plan(uid)
    params = {"event_date": data["event_date"], "distance": data["distance"], "runs_per_week": None,
              "goal_time": data.get("goal_time", ""), "source": "custom", "name": data.get("name", "")}
    db.save_plan(uid, params, old["stats"] if old else DEFAULT_STATS, plan_to_dicts(days))
    return len(days)


if __name__ == "__main__":
    athlete, path = int(sys.argv[1]), sys.argv[2]
    db.init()
    n = load(athlete, json.loads(open(path, encoding="utf-8").read()))
    service.refresh_summary(athlete, force=True)  # new target: rewrite the condition summary
    service.ensure_notes(athlete)
    print(f"imported {n} days for athlete {athlete}")
