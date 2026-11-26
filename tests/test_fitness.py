from datetime import date, timedelta

from app.fitness import metrics, run_load, series

TODAY = date(2026, 11, 27)
THR = 330  # 5:30/km threshold


def run(days_ago, km=10, pace=360, hr=None):
    return {"date": (TODAY - timedelta(days=days_ago)).isoformat(), "km": km, "moving_s": km * pace, "avg_hr": hr}


def test_one_hour_at_threshold_is_about_100():
    assert round(run_load(10.909, 3600, 330)) == 100
    assert run_load(0, 0, 330) == 0


def test_no_runs_is_all_zero():
    m = metrics([], THR, TODAY)
    assert m["today"]["fitness"] == 0 and m["km_last_7_days"] == 0
    assert m["metres_per_heartbeat_last_28_days"] is None


def test_hard_day_raises_fatigue_faster_than_fitness_and_lowers_next_form():
    s = series([run(1, km=20)], THR, TODAY)
    y, t = s[(TODAY - timedelta(days=1)).isoformat()], s[TODAY.isoformat()]
    assert y["fatigue"] > y["fitness"] > 0
    assert t["form"] < 0  # tired the day after


def test_consistent_training_builds_fitness_and_weekly_numbers():
    acts = [run(d) for d in range(0, 56, 2)]
    m = metrics(acts, THR, TODAY)
    assert m["today"]["fitness"] > m["four_weeks_ago"]["fitness"] > 0
    assert m["runs_last_7_days"] == 4 and m["km_last_7_days"] == 40  # days 0, 2, 4, 6 (window excludes day 7)


def test_efficiency_improves_when_same_pace_costs_fewer_beats():
    acts = [run(d, hr=160) for d in range(30, 56, 3)] + [run(d, hr=145) for d in range(0, 28, 3)]
    m = metrics(acts, THR, TODAY)
    assert m["metres_per_heartbeat_last_28_days"] > m["metres_per_heartbeat_previous_28_days"]


def test_changes_are_precomputed_with_direction():
    m = metrics([run(1, km=20)], THR, TODAY)
    assert m["change_vs_yesterday"]["fatigue"].startswith("fatigue down")  # decays the day after a hard run
    assert m["change_vs_week_ago"]["fitness"].startswith("fitness up")
