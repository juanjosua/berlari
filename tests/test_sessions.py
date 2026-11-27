from app.sessions import check, day_state, from_legacy, hard_blocks


def walk(minutes, hr=None):
    return {"type": "Walk", "km": minutes / 10, "moving_min": minutes, "avg_hr": hr}


def run(km, minutes, hr=None, max_hr=None, splits=None, blocks=None):
    return {"type": "Run", "km": km, "moving_min": minutes, "avg_hr": hr, "max_hr": max_hr,
            "km_splits": splits, "hard_blocks": blocks}


def test_easy_walk_checks_duration_and_heart_rate_cap():
    ew = {"type": "EW", "minutes": 40, "hr_max": 132}
    assert check(ew, [walk(42, 128)], True, 190)["state"] == "done"
    c = check(ew, [walk(42, 141)], True, 190)
    assert c["state"] == "partial" and "132" in c["en"] and "132" in c["id"]
    assert check(ew, [walk(20, 120)], True, 190)["state"] == "partial"  # too short
    assert check(ew, [run(5, 40)], True, 190)["state"] == "missed"  # a run isn't a walk
    assert check(ew, [], False, 190)["state"] is None  # today, not done yet


def test_run_walk_accepts_run_or_walk_and_long_run_uses_km():
    assert check({"type": "RW", "minutes": 45}, [run(5, 46)], True, 190)["state"] == "done"
    assert check({"type": "RW", "minutes": 45}, [walk(45)], True, 190)["state"] == "done"
    assert check({"type": "LONG", "km": 10}, [run(7, 80)], True, 190)["state"] == "partial"
    assert check({"type": "LONG", "km": 10}, [run(9.5, 90)], True, 190)["state"] == "done"


def test_tempo_intervals_and_norwegian_4x4_use_pace_and_heart_rate():
    tempo = {"type": "TEMPO", "km": 7, "tempo_km": 4, "pace": 310}
    assert check(tempo, [run(7, 40, splits=["6:00/km", "5:12/km", "5:08/km", "5:15/km", "5:10/km", "6:00/km"])],
                 True, 190)["state"] == "done"
    assert check(tempo, [run(7, 42, splits=["6:00/km"] * 7)], True, 190)["state"] == "partial"
    assert check({"type": "INT", "km": 6}, [run(6, 40, max_hr=150)], True, 190)["state"] == "partial"
    assert check({"type": "INT", "km": 6}, [run(6, 40, max_hr=178)], True, 190)["state"] == "done"
    n4 = {"type": "N4X4", "minutes": 40}
    assert check(n4, [run(5, 40, hr=150, blocks=4)], True, 190)["state"] == "done"
    assert check(n4, [run(5, 40, hr=150, blocks=2)], True, 190)["state"] == "partial"
    assert check(n4, [run(5, 40)], True, 190)["state"] == "done"  # no HR: duration only, says so


def test_strength_strides_and_rest():
    sbw = {"type": "SBW", "rounds": 2}
    assert check(sbw, [{"type": "WeightTraining", "km": 0, "moving_min": 22}], True, 190)["state"] == "done"
    assert check(sbw, [], True, 190)["state"] == "unverified"  # never "missed": we can't see it
    assert check(sbw, [], False, 190)["state"] is None  # upcoming: no hint yet
    assert check({"type": "STRIDES"}, [run(5, 30)], True, 190)["state"] == "unverified"
    assert check({"type": "REST"}, [], True, 190)["state"] is None


def test_day_state_combines_checks():
    s = [{"type": "SBW"}, {"type": "EW", "minutes": 30}]
    done = [check(x, [walk(32)], True, 190) for x in s]
    assert day_state(done, [walk(32)], s, True) == "done"
    missed = [check(x, [], True, 190) for x in s]
    assert day_state(missed, [], s, True) == "missed"
    rest = [{"type": "REST"}]
    assert day_state([check(rest[0], [run(5, 30)], True, 190)], [run(5, 30)], rest, True) == "extra"
    assert from_legacy({"kind": "easy", "km": 6, "detail": "Easy at 6:25/km"})[0]["type"] == "EASY"


def test_hard_blocks_counts_long_high_heart_rate_stretches():
    t = list(range(0, 1800, 5))
    hr = [175 if (i % 420) < 240 else 130 for i in t]  # 4 min hard / 3 min easy, repeated
    assert hard_blocks(hr, t, threshold=160) == 4  # 4 full 7-min cycles; the 5th hard stretch is under 3 min
    assert hard_blocks([170] * 10, list(range(0, 50, 5)), threshold=160) == 0  # too short


def test_example_custom_plan_imports(tmp_path, monkeypatch):
    import json
    import os
    import time
    from pathlib import Path
    os.environ.setdefault("SECRET_KEY", "test")
    from app import db, import_plan
    monkeypatch.setattr(db, "PATH", str(tmp_path / "t.db"))
    db.init()
    db.save_user(9, "Runner", "a", "r", int(time.time()) + 3600)
    data = json.loads((Path(__file__).parents[1] / "examples" / "bfi-run-2027-half-marathon.json")
                      .read_text(encoding="utf-8"))
    assert import_plan.load(9, data) == 186
    plan = db.get_plan(9)
    assert plan["params"]["source"] == "custom" and plan["days"][-1]["kind"] == "race"
    sat = next(d for d in plan["days"] if d["date"] == "2026-11-28")
    assert [s["type"] for s in sat["sessions"]] == ["SBW", "EW"] and sat["kind"] == "walk"
    bad = {**data, "days": [{"date": "2027-01-01", "sessions": [{"type": "SWIM"}]}]}
    try:
        import_plan.load(9, bad)
        assert False, "bad session type accepted"
    except ValueError:
        pass
