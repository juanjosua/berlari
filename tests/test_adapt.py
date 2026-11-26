from datetime import date, timedelta

from app.plan import adapt

MON = date(2026, 11, 30)  # a Monday


def week(start: date, kinds: str, km=(5, 0, 6, 0, 5, 0, 12)):
    """kinds: 7 letters, e=easy r=rest t=tempo i=intervals l=long."""
    names = {"e": "easy", "r": "rest", "t": "tempo", "i": "intervals", "l": "long"}
    return {(start + timedelta(days=i)).isoformat(): {"date": (start + timedelta(days=i)).isoformat(),
            "kind": names[k], "km": float(km[i]), "detail": f"{names[k]} detail", "why": "old note"}
            for i, k in enumerate(kinds)}


def plan(weeks=3, kinds="ereirel"):
    out = {}
    for w in range(weeks):
        out |= week(MON + timedelta(weeks=w), kinds)
    return out


def d(n):  # date n days after MON
    return (MON + timedelta(days=n)).isoformat()


def full(p, upto):  # every planned km actually run before `upto`
    return {k: v["km"] for k, v in p.items() if k < upto and v["km"]}


def test_missed_long_run_moves_to_tomorrow_and_next_hard_day_goes_easy():
    p = plan()
    p[d(8)]["kind"] = "tempo"  # Tue after the missed Sunday long run is hard
    p[d(7)]["kind"], p[d(9)]["kind"] = "rest", "intervals"
    ran = full(p, d(6))  # ran everything Mon-Sat, skipped Sunday's 12 km long run
    changes = adapt(p, ran, d(7), 0)  # Monday evening job
    assert p[d(8)]["kind"] == "long" and p[d(8)]["km"] == 12 and "moved" in p[d(8)]["adjusted"].lower()
    assert "why" not in p[d(8)]  # note rewritten for the new session
    assert p[d(9)]["kind"] == "easy"
    assert len(changes) == 2
    assert adapt(p, ran, d(7), 0) == []  # running the job again changes nothing


def test_missed_long_run_dropped_when_next_long_too_close():
    p = plan(kinds="ereirll")  # Sat and Sun both long: Sat missed, Sunday's long run is today
    ran = full(p, d(5))
    assert not any("moved" in c.lower() for c in adapt(p, ran, d(6), 0))
    assert p[d(7)]["kind"] == "easy"


def test_short_week_shortens_this_weeks_easy_and_long_runs():
    p = plan()
    ran = {d(0): 5.0}  # only 5 of 28 km last week
    before = {k: v["km"] for k, v in p.items()}
    changes = adapt(p, ran, d(7), 0)  # Monday of week 2
    assert changes
    assert p[d(13)]["km"] < before[d(13)] and p[d(13)]["km"] >= before[d(13)] * 0.6  # long run, max 40% cut
    assert p[d(10)]["km"] == before[d(10)]  # hard session (Thu intervals) untouched
    assert p[d(9)]["km"] < before[d(9)]  # Wed easy shortened
    assert p[d(7)]["km"] == before[d(7)]  # today untouched
    assert adapt(p, ran, d(7), 0) == []  # week checked once


def test_full_week_and_extra_running_change_nothing():
    p = plan()
    ran = {k: v * 1.5 for k, v in full(p, d(7)).items()}
    assert adapt(p, ran, d(7), 0) == []


def test_very_tired_turns_tomorrows_hard_session_easy():
    p = plan()
    changes = adapt(p, full(p, d(9)), d(9), -25)  # tomorrow (Thu d10) is intervals
    assert p[d(10)]["kind"] == "easy" and "tired" in changes[-1]
    p2 = plan()
    assert not any("tired" in c for c in adapt(p2, full(p2, d(9)), d(9), -15))
