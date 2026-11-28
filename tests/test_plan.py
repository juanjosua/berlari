from datetime import date

import pytest

from app.plan import Stats, build_plan, weekly_targets

TODAY = date(2026, 11, 25)  # a Wednesday
STATS = Stats(weekly_km=20, longest_km=10, easy_pace_s=390)


def test_plan_ends_on_race_day_and_starts_today():
    days = build_plan(STATS, "half", date(2027, 3, 7), 4, today=TODAY)
    assert days[0].date == TODAY.isoformat()
    assert days[-1].kind == "race" and days[-1].date == "2027-03-07"
    assert len({d.date for d in days}) == len(days)  # one entry per day


def test_runs_per_week_respected_and_strength_twice_a_week():
    days = build_plan(STATS, "10k", date(2027, 2, 28), 3, today=date(2026, 11, 23))
    first_week = days[:7]
    assert sum(d.kind not in ("rest", "strength") for d in first_week) == 3
    assert sum(any(x["type"] == "SBW" for x in d.sessions) for d in first_week) == 2


def test_beginner_gets_run_walk_and_norwegian_4x4_then_progresses():
    days = build_plan(Stats(6, 4, 560), "half", date(2027, 5, 30), 4, today=date(2026, 11, 23))
    types = lambda ds: {x["type"] for d in ds for x in d.sessions}  # noqa: E731
    vars_ = lambda ds: {x.get("var") for d in ds for x in d.sessions}  # noqa: E731
    assert types(days) <= {"EASY", "LONG", "TEMPO", "INT", "SBW", "REST", "RACE"}  # only the app's own categories
    assert {"runwalk", "walk_breaks", "n4x4"} <= vars_(days[:14])
    assert {"EASY", "LONG"} <= types(days[-60:])
    assert "strides" in {x.get("var") for d in days[-60:] for x in d.sessions}
    assert days[-1].kind == "race" and not any(x["type"] == "SBW" for d in days[-4:] for x in d.sessions)


def test_volume_growth_capped_and_taper_drops():
    vols = weekly_targets(20, 55, 14, 2)
    for i in range(1, len(vols) - 2):  # after a cutback, resuming the previous peak is fine
        assert vols[i] <= max(vols[:i]) * 1.10 + 0.1
    assert vols[-1] < vols[-3] and vols[-2] < vols[-3]


def test_long_run_never_exceeds_cap():
    days = build_plan(Stats(60, 30, 330), "marathon", date(2027, 6, 1), 5, today=TODAY)
    assert max(d.km for d in days if d.kind == "long") <= 32


def test_goal_time_sets_race_pace():
    days = build_plan(STATS, "10k", date(2027, 1, 31), 4, goal_s=50 * 60, today=TODAY)
    assert "5:00/km" in days[-1].detail


def test_past_event_rejected():
    with pytest.raises(ValueError):
        build_plan(STATS, "5k", TODAY, 4, today=TODAY)




def test_personal_default_variations_replace_recommendations():
    from app.plan import Stats as S_
    prefs = {"INT": "n4x4", "EASY": "runwalk", "LONG": "walk_breaks", "SBW": "classic"}
    days = build_plan(S_(30, 14, 360), "half", date(2027, 5, 30), 4, today=date(2026, 11, 23), prefs=prefs)
    for d in days:
        for x in d.sessions:
            fam = {"INT": "INT", "EASY": "EASY", "LONG": "LONG", "SBW": "SBW"}.get(x["type"])
            if fam:
                assert x["var"] == prefs[fam] and x.get("rec"), x
    plain = build_plan(S_(30, 14, 360), "half", date(2027, 5, 30), 4, today=date(2026, 11, 23))
    assert len({x["var"] for d in plain for x in d.sessions if x["type"] == "INT"}) > 1  # rotates without prefs


def test_phases_checkpoints_evaluation_and_adjustment():
    from app.plan import adjust_after_failed_phase, evaluate_phase, phase_message, plan_phases
    days = [d.__dict__ for d in build_plan(Stats(8, 4.6, 565), "half", date(2027, 5, 30), 4, 10800,
                                           today=date(2026, 11, 28))]
    phases = plan_phases(days)
    assert [p["key"] for p in phases] == ["base", "build1", "build2", "peak", "taper"]
    assert all(p["checkpoint"] for p in phases[:-1]) and phases[-1]["checkpoint"] is None
    base = phases[0]
    in_base = [d for d in days if base["start"] <= d["date"] <= base["end"]]

    def checked(state_for):
        return [d | {"checks": [{"state": state_for(d, x)} for x in d["sessions"]]} for d in in_base]
    good = evaluate_phase(base, checked(lambda d, x: None if x["type"] in ("REST", "SBW") else "done"))
    assert good["passed"] and good["ratio"] == 1.0
    # long run on checkpoint day missed -> fails even with most sessions done
    bad = evaluate_phase(base, checked(lambda d, x: None if x["type"] in ("REST", "SBW") else
                                       "missed" if d["date"] == base["checkpoint"] else "done"))
    assert not bad["passed"] and bad["checkpoint_state"] == "missed"
    by_date = {d["date"]: d for d in days}
    before = {k: v["km"] for k, v in by_date.items() if v["phase"] == "build1"}
    n = adjust_after_failed_phase(by_date, "build1", base["checkpoint"])
    assert n > 0 and all(by_date[k]["km"] <= km for k, km in before.items())
    assert {x["var"] for d in by_date.values() if d["phase"] == "build1" for x in d["sessions"]
            if x["type"] == "LONG"} == {"walk_breaks"}
    msg = phase_message(bad | {"phase": "base", "next": "build1", "adjusted": n})
    assert "not reached" in msg and "lighter" in msg
    assert "belum tercapai" in phase_message(bad | {"phase": "base", "next": "build1", "adjusted": n}, "id")


def test_paces_follow_race_pace_logic():
    from app.plan import paces
    p = paces(STATS, "half", 3 * 3600)  # 3:00 half = 8:32/km race pace
    assert p["interval"] < p["tempo"] < p["race"] < p["easy"]  # tempo must be faster than half-marathon pace
    assert round(p["race"]) == 512 and round(p["tempo"]) == 500 and round(p["easy"]) == 572
    q = paces(STATS, "5k", 30 * 60)
    assert q["interval"] < q["race"] < q["tempo"] < q["easy"]  # 5K race pace is faster than tempo


def test_beginner_half_peaks_lower_with_last_long_run_three_weeks_out():
    from datetime import timedelta
    race = date(2027, 5, 30)
    days = build_plan(Stats(7, 4.6, 565), "half", race, 4, 3 * 3600, today=date(2026, 11, 28))
    weeks = {}
    for d in days:
        k = date.fromisoformat(d.date) - timedelta(days=date.fromisoformat(d.date).weekday())
        weeks[k] = weeks.get(k, 0) + d.km
    assert max(weeks.values()) <= 40  # beginner cap (38 km) instead of 55
    longs = [(d.date, x["km"]) for d in days for x in d.sessions if x["type"] == "LONG"]
    peak_km = max(km for _, km in longs)
    assert 16 <= peak_km <= 21
    last_peak = max(dt for dt, km in longs if km == peak_km)
    assert (race - date.fromisoformat(last_peak)).days >= 20  # biggest long run ~3 weeks before the race
    race_week = [d for d in days if (race - date.fromisoformat(d.date)).days < 7]
    assert sum(d.km for d in race_week if d.kind != "race") < 12  # light race week
    assert any(x["type"] == "TEMPO" for d in days if d.phase in ("build2", "peak") for x in d.sessions)


def test_higher_bmi_builds_slower_peaks_lower_and_keeps_run_walk_longer():
    from datetime import timedelta
    from app.plan import body_tier
    assert [body_tier(b) for b in (None, 24.0, 31.0, 35.3)] == [0, 0, 1, 2]

    def summary(bmi):
        days = build_plan(Stats(7, 4.6, 565), "half", date(2027, 5, 30), 4, 3 * 3600, today=date(2026, 11, 28), bmi=bmi)
        weeks = {}
        for d in days:
            k = date.fromisoformat(d.date) - timedelta(days=date.fromisoformat(d.date).weekday())
            weeks[k] = weeks.get(k, 0) + d.km
        longs = [x["km"] for d in days for x in d.sessions if x["type"] == "LONG"]
        build2_vars = {x.get("var") for d in days if d.phase == "build2" for x in d.sessions if x["type"] in ("EASY", "LONG")}
        return max(weeks.values()), max(longs), build2_vars
    normal, heavy = summary(None), summary(35.3)
    assert heavy[0] < normal[0] * 0.85  # lower peak week
    assert 14 <= heavy[1] <= normal[1]  # long run still reaches ~15 km
    assert heavy[2] <= {"runwalk", "walk_breaks"} and not normal[2] <= {"runwalk", "walk_breaks"}
