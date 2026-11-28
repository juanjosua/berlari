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
    r = c.post("/new", data={"event_date": event, "distance": "10k", "runs_per_week": 4, "goal_minutes": "50"})
    assert r.status_code == 303
    page = c.get("/plan").text
    assert "20.0 km/week" in page and "6:00/km" in page  # 10 runs × 8 km in 4 weeks, 6:00 typical pace
    assert "Today and tomorrow" in page and "Full schedule" in page and "Week of" not in page
    ev = date.fromisoformat(event)
    last = c.get("/plan/schedule", params={"week": (ev - timedelta(days=ev.weekday())).isoformat()}).text
    assert "Race day" in last and "5:00/km" in last and "Previous" in last
    first = c.get("/plan/schedule").text  # defaults to this week
    assert "Week 1/" in first and "Next" in first

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


def test_parse_goal_minutes():
    import pytest
    assert main.parse_goal("") is None and main.parse_goal("119") == 119 * 60
    for bad in ("1:59", "5", "abc", "-30"):
        with pytest.raises(ValueError):
            main.parse_goal(bad)


def test_admin_only_for_allowlisted_athletes_and_support_page(monkeypatch):
    def login(uid):
        monkeypatch.setattr(strava, "exchange_code", lambda code: (
            db.save_user(uid, f"Runner {uid}", "a", "r", int(time.time()) + 3600), {"athlete": {"id": uid}})[1])
        c = TestClient(main.app, follow_redirects=False)
        state = c.get("/auth/login").headers["location"].split("state=")[1]
        c.get("/auth/callback", params={"code": "x", "state": state})
        return c

    db.init()  # earlier test removes the test database file
    monkeypatch.setattr(main, "ADMIN_IDS", {501})
    assert TestClient(main.app).get("/admin").status_code == 404  # logged out
    assert login(502).get("/admin").status_code == 404  # not an admin
    page = login(501).get("/admin").text
    assert "Runner 501" in page and "Runner 502" in page and "of 10 connected" in page
    assert "github.com/juanjosua/berlari/issues" in TestClient(main.app).get("/support").text
    db.delete_user(501), db.delete_user(502)


def test_admin_remove_deauthorizes_and_deletes(monkeypatch):
    db.init()
    revoked = []
    monkeypatch.setattr(strava, "deauthorize", lambda u: revoked.append(u["id"]))
    monkeypatch.setattr(main, "ADMIN_IDS", {601})
    db.save_user(602, "Friend <script>", "a", "r", int(time.time()) + 3600)
    monkeypatch.setattr(strava, "exchange_code", lambda code: (
        db.save_user(601, "Admin", "a", "r", int(time.time()) + 3600), {"athlete": {"id": 601}})[1])
    c = TestClient(main.app, follow_redirects=False)
    state = c.get("/auth/login").headers["location"].split("state=")[1]
    c.get("/auth/callback", params={"code": "x", "state": state})

    page = c.get("/admin").text
    assert "Friend <script>" not in page and "Friend &lt;script&gt;" in page  # name escaped
    assert TestClient(main.app).post("/admin/remove/602").status_code == 404  # not logged in
    r = c.post("/admin/remove/602")
    assert r.status_code == 303 and revoked == [602] and db.get_user(602) is None
    c.post("/admin/remove/601")
    assert db.get_user(601) is not None  # can't remove yourself
    db.delete_user(601)


def test_language_switch(monkeypatch):
    from app import coach, service
    db.init()
    monkeypatch.setenv("GROQ_SECRET_KEY", "fake")
    langs = []
    monkeypatch.setattr(coach, "daily_summary", lambda m, r, p, prev, lang="en": langs.append(lang) or
                        {"headline": "Kondisi bagus", "better": [], "watch": [], "next": ""})
    monkeypatch.setattr(coach, "explain_days", lambda days, ctx, lang="en": {d["date"]: "x" for d in days})
    monkeypatch.setattr(strava, "exchange_code", lambda code: (
        db.save_user(701, "Budi Lari", "a", "r", int(time.time()) + 3600), {"athlete": {"id": 701}})[1])
    monkeypatch.setattr(strava, "recent_runs", lambda u: [])
    c = TestClient(main.app, follow_redirects=False)
    assert "Your training plan" in c.get("/").text
    assert "Program latihanmu" in c.get("/", headers={"accept-language": "id-ID,id;q=0.9"}).text

    state = c.get("/auth/login").headers["location"].split("state=")[1]
    c.get("/auth/callback", params={"code": "x", "state": state})
    c.post("/new", data={"event_date": (date.today() + timedelta(weeks=8)).isoformat(), "distance": "10k"})
    assert langs == ["en"]

    r = c.post("/lang/id", data={"next": "/plan"})
    assert r.status_code == 303 and r.headers["location"] == "/plan" and "lang=id" in r.headers["set-cookie"]
    assert db.get_user(701)["lang"] == "id" and langs == ["en", "id"]  # summary rewritten in Indonesian
    page = c.get("/plan").text
    assert "Kondisi bagus" in page and "Kondisimu saat ini" in page
    assert '<html lang="id">' in page and "Keluar" in page
    c.post("/lang/id", data={"next": "/plan"})
    assert langs == ["en", "id"]  # same language: nothing regenerated
    assert c.post("/lang/id", data={"next": "//evil.example"}).headers["location"] == "/"
    assert c.post("/lang/xx", data={"next": "/"}).status_code == 404
    db.delete_user(701)


def test_bucket_stream_into_5_second_samples():
    data = {"time": {"data": [0, 1, 2, 5, 6, 30, 31]}, "velocity_smooth": {"data": [3, 3, 3, 4, 4, 2, 2]},
            "heartrate": {"data": [100, 110, 120, 130, 140, 150, 160]}}
    out = strava.bucket(data)
    assert out["v"] == [3.0, 4.0, 2.0] and out["hr"] == [110, 135, 155]  # paused gap 7-29 s dropped
    assert strava.bucket({"time": {"data": [0]}}) is None  # no speed (treadmill without GPS)


def test_choose_variation_only_for_upcoming_sessions(monkeypatch):
    from app import service
    db.init()
    monkeypatch.setattr(strava, "exchange_code", lambda code: (
        db.save_user(801, "Var Runner", "a", "r", int(time.time()) + 3600), {"athlete": {"id": 801}})[1])
    monkeypatch.setattr(strava, "recent_runs", lambda u: [])
    c = TestClient(main.app, follow_redirects=False)
    state = c.get("/auth/login").headers["location"].split("state=")[1]
    c.get("/auth/callback", params={"code": "x", "state": state})
    c.post("/new", data={"event_date": (date.today() + timedelta(weeks=12)).isoformat(), "distance": "10k"})
    days = db.get_plan(801)["days"]
    d = next(x for x in days if x["date"] > date.today().isoformat() and any(s["type"] == "LONG" for s in x["sessions"]))
    idx = next(i for i, s in enumerate(d["sessions"]) if s["type"] == "LONG")  # beginners start with LRW weeks
    assert "Choose another variation" in c.get("/plan").text
    c.post("/plan/variation", data={"day": d["date"], "idx": idx, "var": "fast_finish"})
    assert next(x for x in db.get_plan(801)["days"] if x["date"] == d["date"])["sessions"][idx]["var"] == "fast_finish"
    assert not service.set_variation(801, d["date"], idx, "sprints")  # not a long-run variation
    assert not service.set_variation(801, "2000-01-01", 0, "classic")  # past/unknown day
    db.delete_user(801)


def test_settings_age_gives_tanaka_max_hr_and_defaults_apply(monkeypatch):
    from app import service
    db.init()
    monkeypatch.setattr(strava, "exchange_code", lambda code: (
        db.save_user(901, "Set Runner", "a", "r", int(time.time()) + 3600), {"athlete": {"id": 901}})[1])
    monkeypatch.setattr(strava, "recent_runs", lambda u: [])
    c = TestClient(main.app, follow_redirects=False)
    state = c.get("/auth/login").headers["location"].split("state=")[1]
    c.get("/auth/callback", params={"code": "x", "state": state})
    c.post("/new", data={"event_date": (date.today() + timedelta(weeks=16)).isoformat(), "distance": "10k"})
    c.post("/settings", data={"age": "30", "var_INT": "fartlek", "var_EASY": "", "var_LONG": "bogus"})
    assert service.max_hr_info(901) == (187, "tanaka")  # 208 - 0.7 * 30 = 187
    future = [x for d in db.get_plan(901)["days"] if d["date"] >= date.today().isoformat()
              for x in d["sessions"] if x["type"] == "INT"]
    assert future and all(x["var"] == "fartlek" for x in future)
    page = c.get("/plan").text
    assert "187 bpm" in page and "Tanaka" in page and "Checkpoint" in page
    assert "Settings" in c.get("/settings").text
    db.delete_user(901)
