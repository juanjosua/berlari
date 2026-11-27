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
    assert {"RW", "LRW", "N4X4", "SBW"} <= types(days[:14])
    assert "INT" not in types(days)
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


