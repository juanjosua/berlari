"""End-to-end flow with Strava mocked out."""
import os
import time
from datetime import date, timedelta

os.environ.setdefault("SECRET_KEY", "test")
os.environ.setdefault("STRAVA_CLIENT_ID", "1")
os.environ["BERLARI_DB"] = os.path.join(os.path.dirname(__file__), "test.db")

from fastapi.testclient import TestClient  # noqa: E402

from app import db, main, strava  # noqa: E402


def test_login_plan_forget(monkeypatch):
    def fake_exchange(code):
        db.save_user(42, "Test Runner", "a", "r", int(time.time()) + 3600)
        return {"athlete": {"id": 42}}

    now = date.today()
    runs = [{"id": i, "start_date": f"{now - timedelta(days=i * 3)}T06:00:00Z", "distance": 8000.0,
             "start_date_local": f"{now - timedelta(days=i * 3)}T06:00:00Z",
             "moving_time": 8 * 360, "sport_type": "Run"} for i in range(10)]
    monkeypatch.setattr(strava, "exchange_code", fake_exchange)
    monkeypatch.setattr(strava, "recent_runs", lambda user: runs)

    c = TestClient(main.app, follow_redirects=False)
    r = c.get("/auth/login")
    assert "strava.com/oauth/authorize" in r.headers["location"]
    state = r.headers["location"].split("state=")[1]
    assert c.get("/auth/callback", params={"code": "x", "state": "bad"}).status_code == 200  # rejected
    r = c.get("/auth/login")
    state = r.headers["location"].split("state=")[1]
    assert c.get("/auth/callback", params={"code": "x", "state": state}).headers["location"] == "/"

    event = (now + timedelta(weeks=10)).isoformat()
    r = c.post("/new", data={"event_date": event, "distance": "10k", "runs_per_week": 4, "goal_time": "50:00"})
    assert r.status_code == 303
    page = c.get("/plan").text
    assert "Race day" in page and "5:00/km" in page
    assert "20.0 km/week" in page and "6:00/km" in page  # 10 runs × 8 km in 4 weeks, 6:00 typical pace

    assert c.post("/new", data={"event_date": "2000-01-01", "distance": "10k"}).status_code == 400
    c.post("/forget")
    assert db.get_user(42) is None
    os.remove(os.environ["BERLARI_DB"])


def test_brand_assets_and_privacy():
    c = TestClient(main.app)
    home = c.get("/").text
    assert "https://www.strava.com/oauth/authorize" in home and "strava-connect.svg" in home
    assert "strava-powered-black.svg" in home
    assert "Delete my data" in c.get("/privacy").text
