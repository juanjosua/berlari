"""Coach text + Strava webhook flow, with Strava and Groq mocked."""
import os
import time
from datetime import date, timedelta

os.environ.setdefault("SECRET_KEY", "test")
os.environ.setdefault("STRAVA_CLIENT_ID", "1")
os.environ["BERLARI_DB"] = os.path.join(os.path.dirname(__file__), "test.db")

from fastapi.testclient import TestClient  # noqa: E402

from app import coach, db, main, strava  # noqa: E402


def test_coach_and_webhook(monkeypatch):
    monkeypatch.setenv("GROQ_SECRET_KEY", "fake")
    db.init()
    db.delete_user(7)
    today = date.today()
    calls = []
    monkeypatch.setattr(coach, "fitness_summary", lambda p, params: calls.append("sum") or "Solid base.")
    monkeypatch.setattr(coach, "explain_week",
                        lambda days, s, p: calls.append("week") or {d["date"]: f"why {d['kind']}" for d in days})
    monkeypatch.setattr(coach, "review_session", lambda d, a, s, p: calls.append("rev") or f"Nice {a['total_km']} km")
    monkeypatch.setattr(strava, "exchange_code", lambda code: (
        db.save_user(7, "Runner", "a", "r", int(time.time()) + 3600), {"athlete": {"id": 7}})[1])
    monkeypatch.setattr(strava, "recent_runs", lambda u: [
        {"start_date": f"{today - timedelta(days=i * 3)}T06:00:00Z", "distance": 8000.0,
         "moving_time": 2880, "sport_type": "Run", "average_heartrate": 150} for i in range(10)])

    c = TestClient(main.app, follow_redirects=False)
    state = c.get("/auth/login").headers["location"].split("state=")[1]
    c.get("/auth/callback", params={"code": "x", "state": state})
    c.post("/new", data={"event_date": (today + timedelta(weeks=8)).isoformat(), "distance": "10k"})
    page = c.get("/plan").text
    assert "Solid base." in page and "why " in page
    weeks_called = calls.count("week")
    c.get("/plan")
    assert calls.count("week") == weeks_called  # already explained: no new LLM calls

    # webhook verification handshake
    assert c.get("/strava/webhook", params={"hub.verify_token": "nope", "hub.challenge": "z"}).status_code == 403
    r = c.get("/strava/webhook", params={"hub.verify_token": main.VERIFY_TOKEN, "hub.challenge": "z"})
    assert r.json() == {"hub.challenge": "z"}

    # a run uploaded today gets attached, statused and reviewed
    act = {"id": 99, "sport_type": "Run", "distance": 9000.0, "moving_time": 3000, "total_elevation_gain": 20,
           "start_date_local": f"{today}T07:00:00Z", "average_heartrate": 148, "max_heartrate": 170}
    monkeypatch.setattr(strava, "get_activity", lambda u, aid: act)
    ev = {"object_type": "activity", "object_id": 99, "aspect_type": "create", "owner_id": 7}
    assert c.post("/strava/webhook", json=ev).status_code == 200
    page = c.get("/plan").text
    assert "Ran 9 km" in page and "Nice 9.0 km" in page
    c.post("/strava/webhook", json=ev | {"aspect_type": "update"})
    assert calls.count("rev") == 1  # edits don't re-run the review

    c.post("/strava/webhook", json=ev | {"aspect_type": "delete"})
    assert "Ran 9 km" not in c.get("/plan").text

    # athlete revokes access on Strava -> data deleted
    c.post("/strava/webhook", json={"object_type": "athlete", "owner_id": 7, "updates": {"authorized": "false"}})
    assert db.get_user(7) is None and db.get_plan(7) is None
