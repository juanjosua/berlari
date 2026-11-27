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


def b(sec, speed):  # 5-second buckets at a speed (m/s)
    return [speed] * (sec // 5)


def srun(v, hr=None, avg=None, km=8.0, typ="Run", elev=0):
    return {"type": typ, "km": km, "moving_min": len(v) * 5 / 60, "avg_hr": avg, "elev_gain_m": elev,
            "stream": {"v": v, "hr": hr}}


PACES = {"easy": 360, "tempo": 310, "interval": 280, "race": 330}
EASY, FAST = 2.7, 3.8


def var_state(type_, var, act, **kw):
    return check({"type": type_, "var": var, **kw}, [act], True, 190, PACES)


def test_interval_variations_count_fast_efforts():
    track = b(600, EASY) + sum((b(200, FAST) + b(150, EASY) for _ in range(6)), []) + b(600, EASY)
    assert var_state("INT", "track", srun(track))["state"] == "done"
    assert var_state("INT", "track", srun(b(3000, EASY)))["state"] == "partial"
    hiit = b(600, EASY) + sum((b(30, FAST) + b(30, EASY) for _ in range(12)), []) + b(300, EASY)
    assert var_state("INT", "hiit", srun(hiit))["state"] == "done"
    sprints = b(600, 2.0) + sum((b(20, 4.6) + b(150, 2.0) for _ in range(8)), [])
    assert var_state("INT", "sprints", srun(sprints))["state"] == "done"
    pyramid = b(600, EASY) + sum((b(x, FAST) + b(x, EASY) for x in (60, 120, 180, 120, 60)), [])
    assert var_state("INT", "pyramid", srun(pyramid))["state"] == "done"
    fartlek = sum((b(240, EASY) + b(90, FAST) for _ in range(8)), [])
    c = var_state("INT", "fartlek", srun(fartlek))
    assert c["state"] == "done" and "Fartlek ✓" in c["en"]
    assert var_state("INT", "fartlek", srun(b(2400, EASY)))["state"] == "partial"


def test_tempo_variations_use_tempo_pace():
    T = 1000 / 310 + 0.05
    assert var_state("TEMPO", "steady", srun(b(600, EASY) + b(1500, T) + b(600, EASY)))["state"] == "done"
    c = var_state("TEMPO", "steady", srun(b(600, EASY) + b(480, T) + b(600, EASY)))
    assert c["state"] == "partial" and "8 min" in c["en"]
    cruise = b(600, EASY) + sum((b(300, T) + b(60, EASY) for _ in range(5)), [])
    assert var_state("TEMPO", "cruise", srun(cruise))["state"] == "done"
    assert var_state("TEMPO", "progressive", srun(b(1200, EASY) + b(900, T)))["state"] == "done"
    assert var_state("TEMPO", "progressive", srun(b(2100, EASY)))["state"] == "partial"


def test_easy_and_long_variations():
    assert var_state("EASY", "aerobic", srun(b(2400, EASY), avg=135))["state"] == "done"
    assert var_state("EASY", "aerobic", srun(b(2400, EASY), avg=160))["state"] == "partial"  # 75% of 190 = 142
    assert var_state("EASY", "recovery", srun(b(3600, EASY), avg=120))["state"] == "partial"  # too long
    strides = b(2400, EASY) + sum((b(20, 4.2) + b(60, 2.4) for _ in range(6)), [])
    assert var_state("EASY", "strides", srun(strides))["state"] == "done"
    prog = [2.5 + 0.6 * i / 480 for i in range(480)]
    assert var_state("EASY", "progression", srun(prog, km=7))["state"] == "done"
    assert var_state("EASY", "trail", srun(b(2400, EASY), typ="TrailRun"))["state"] == "done"
    assert var_state("EASY", "trail", srun(b(2400, EASY)))["state"] == "partial"
    T = 1000 / 310 + 0.05
    assert var_state("LONG", "fast_finish", srun(b(3600, EASY) + b(900, T), km=16))["state"] == "done"
    R = 1000 / 330
    rp = b(1800, EASY) + b(900, R) + b(300, EASY) + b(900, R) + b(600, EASY)
    assert var_state("LONG", "race_pace", srun(rp, km=18))["state"] == "done"
    assert var_state("LONG", "hilly", srun(b(4800, EASY), km=16, elev=200))["state"] == "done"
    assert var_state("LONG", "classic", srun(b(4800, EASY), km=16, avg=170))["state"] == "partial"


def test_norwegian_4x4_and_missing_stream():
    hr = sum(([130] * 36 + [170] * 48 for _ in range(4)), [])  # 3 min easy / 4 min hard, x4
    assert check({"type": "N4X4"}, [srun(b(len(hr) * 5, EASY), hr=hr)], True, 190)["state"] == "done"
    assert check({"type": "N4X4"}, [srun(b(len(hr) * 5, EASY), hr=hr[:200])], True, 190)["state"] == "partial"
    no_gps = {"type": "Run", "km": 6, "moving_min": 40, "avg_hr": 150}
    c = check({"type": "INT", "var": "track"}, [no_gps], True, 190, PACES)
    assert c["state"] == "done" and "GPS" in c["en"]
    assert check({"type": "INT", "var": "track", "km": 10}, [no_gps], True, 190, PACES)["state"] == "partial"  # too short


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


def test_generic_workout_is_not_counted_as_strength():
    assert check({"type": "SBW"}, [{"type": "Workout", "km": 0, "moving_min": 110}], True, 190)["state"] == "unverified"


def test_title_follows_swapped_interval_variation():
    from app.sessions import label
    assert label({"type": "N4X4"}) == "Norwegian 4x4"
    assert label({"type": "N4X4", "var": "hiit"}) == "Intervals" and label({"type": "N4X4", "var": "hiit"}, "id") == "Interval"
