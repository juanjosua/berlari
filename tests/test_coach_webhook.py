"""Coach text, saving rules and the Strava webhook, with Strava and Groq mocked."""
import os
import time
from datetime import date, timedelta

os.environ.setdefault("SECRET_KEY", "test")
os.environ.setdefault("STRAVA_CLIENT_ID", "1")
os.environ["BERLARI_DB"] = os.path.join(os.path.dirname(__file__), "test.db")

from fastapi.testclient import TestClient  # noqa: E402

from app import coach, db, main, nightly, service, strava  # noqa: E402

DAY0 = date.today()


def run(i, day, km=8.0):
    return {"id": i, "sport_type": "Run", "distance": km * 1000, "moving_time": km * 360,
            "start_date": f"{day}T06:00:00Z", "start_date_local": f"{day}T06:00:00Z",
            "average_heartrate": 150, "max_heartrate": 170, "total_elevation_gain": 10}


def test_coach_rules_and_webhook(monkeypatch):
    monkeypatch.setenv("GROQ_SECRET_KEY", "fake")
    monkeypatch.setattr(nightly.time, "sleep", lambda s: None)
    db.init()
    db.delete_user(7)
    clock = {"today": DAY0}
    monkeypatch.setattr(service, "today", lambda: clock["today"])
    calls = []
    monkeypatch.setattr(coach, "daily_summary", lambda m, r, p, prev, lang="en": calls.append(("sum", m)) or {"headline": f"Summary {len(calls)}", "better": ["Base growing"], "watch": [], "next": "Easy days"})
    monkeypatch.setattr(coach, "explain_days",
                        lambda days, ctx, lang="en": calls.append(("why", [d["date"] for d in days])) or
                        {d["date"]: f"why {d['kind']}" for d in days})
    monkeypatch.setattr(coach, "review_session", lambda d, a, ctx, lang="en": calls.append(("rev",)) or f"Nice {a['total_km']} km")
    monkeypatch.setattr(strava, "exchange_code", lambda code: (
        db.save_user(7, "Runner", "a", "r", int(time.time()) + 3600), {"athlete": {"id": 7}})[1])
    monkeypatch.setattr(strava, "recent_runs", lambda u: [run(i, DAY0 - timedelta(days=i * 3 + 1)) for i in range(10)])

    def count(kind):
        return sum(1 for c in calls if c[0] == kind)

    c = TestClient(main.app, follow_redirects=False)
    state = c.get("/auth/login").headers["location"].split("state=")[1]
    c.get("/auth/callback", params={"code": "x", "state": state})
    c.post("/new", data={"event_date": (DAY0 + timedelta(weeks=8)).isoformat(), "distance": "10k"})

    # Plan creation: one summary, notes only for today + tomorrow (not weeks ahead)
    page = c.get("/plan").text
    assert "Summary 1" in page and "Fitness" in page and "Base growing" in page
    assert "View on Strava" in page and "strava.com/activities/0" in page  # recent runs list
    assert count("sum") == 1 and count("why") == 1
    assert calls[1][1] == [DAY0.isoformat(), (DAY0 + timedelta(days=1)).isoformat()]
    # Refreshing never calls the LLM again
    c.get("/plan"), c.get("/plan")
    assert count("sum") == 1 and count("why") == 1
    # Nightly the same day with no new runs: nothing regenerated
    nightly.main()
    assert count("sum") == 1 and count("why") == 1

    # Webhook handshake
    assert c.get("/strava/webhook", params={"hub.verify_token": "nope", "hub.challenge": "z"}).status_code == 403
    r = c.get("/strava/webhook", params={"hub.verify_token": main.VERIFY_TOKEN, "hub.challenge": "z"})
    assert r.json() == {"hub.challenge": "z"}

    # A run today: attached, statused, reviewed once (edits don't re-review)
    act = run(99, DAY0, km=9.0)
    monkeypatch.setattr(strava, "get_activity", lambda u, aid: act)
    ev = {"object_type": "activity", "object_id": 99, "aspect_type": "create", "owner_id": 7}
    c.post("/strava/webhook", json=ev)
    page = c.get("/plan").text
    assert "9 km · 54" in page and "Nice 9.0 km" in page
    c.post("/strava/webhook", json=ev | {"aspect_type": "update"})
    assert count("rev") == 1

    # Same evening: summary already made today, so not regenerated even though a run came in
    nightly.main()
    assert count("sum") == 1
    # Next evening: new run since last summary -> one new summary, and the next day's note
    clock["today"] = DAY0 + timedelta(days=1)
    nightly.main()
    assert count("sum") == 2 and count("why") == 2
    assert calls[-1][0] == "why" or calls[-2][0] == "why"
    summary_metrics = [c for c in calls if c[0] == "sum"][-1][1]
    assert summary_metrics["today"]["fitness"] > 0 and "yesterday" in summary_metrics
    # Following evening with no new run: no new summary
    clock["today"] = DAY0 + timedelta(days=2)
    nightly.main()
    assert count("sum") == 2

    # Delete the run: removed from the plan along with its review
    clock["today"] = DAY0
    c.post("/strava/webhook", json=ev | {"aspect_type": "delete"})
    page = c.get("/plan").text
    assert "9 km · 54" not in page and "Nice 9.0 km" not in page

    # Athlete revokes access on Strava -> everything deleted
    c.post("/strava/webhook", json={"object_type": "athlete", "owner_id": 7, "updates": {"authorized": "false"}})
    assert db.get_user(7) is None and db.get_plan(7) is None and db.get_activities(7) == []
