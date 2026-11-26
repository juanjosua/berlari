"""Pure fitness/fatigue/form model (no I/O). Same idea as TrainingPeaks' PMC or Strava's Fitness & Freshness.

Each run gets a load score (running TSS): hours × (threshold pace / run pace)² × 100, so one hour at
threshold ≈ 100. Fitness = 42-day exponential average of daily load, fatigue = 7-day average,
form = fitness − fatigue (negative = tired, positive = fresh)."""
from datetime import date, timedelta

FITNESS_DAYS, FATIGUE_DAYS = 42, 7


def run_load(km: float, moving_s: float, threshold_pace_s: float) -> float:
    if km <= 0 or moving_s <= 0:
        return 0.0
    intensity = min(threshold_pace_s / (moving_s / km), 1.3)  # cap: GPS glitches make absurd paces
    return moving_s / 3600 * intensity ** 2 * 100


def series(acts: list[dict], threshold_pace_s: float, until: date) -> dict[str, dict]:
    """{date: {fitness, fatigue, form, load}} for every day from the first activity until `until`.
    acts: [{date: 'YYYY-MM-DD', km, moving_s}]"""
    if not acts:
        return {}
    loads: dict[str, float] = {}
    for a in acts:
        loads[a["date"]] = loads.get(a["date"], 0) + run_load(a["km"], a["moving_s"], threshold_pace_s)
    d, end = date.fromisoformat(min(loads)), until
    fit = fat = 0.0
    out = {}
    while d <= end:
        load = loads.get(d.isoformat(), 0.0)
        form = fit - fat  # form is measured going into the day, before today's load
        fit += (load - fit) / FITNESS_DAYS
        fat += (load - fat) / FATIGUE_DAYS
        out[d.isoformat()] = {"fitness": round(fit, 1), "fatigue": round(fat, 1), "form": round(form, 1),
                              "load": round(load)}
        d += timedelta(days=1)
    return out


def _window(acts, today: date, start_days_ago: int, end_days_ago: int) -> list[dict]:
    lo, hi = (today - timedelta(days=start_days_ago)).isoformat(), (today - timedelta(days=end_days_ago)).isoformat()
    return [a for a in acts if lo < a["date"] <= hi]


def _efficiency(acts) -> float | None:
    """Metres per heartbeat on runs with HR: higher = fitter aerobic engine at the same effort."""
    hr = [a for a in acts if a.get("avg_hr") and a["moving_s"] > 0]
    if not hr:
        return None
    metres = sum(a["km"] * 1000 for a in hr)
    beats = sum(a["avg_hr"] * a["moving_s"] / 60 for a in hr)
    return round(metres / beats, 3)


def metrics(acts: list[dict], threshold_pace_s: float, today: date) -> dict:
    """Today's numbers plus the same numbers yesterday / 7 / 28 days ago, for the coach to compare."""
    s = series(acts, threshold_pace_s, today)
    zero = {"fitness": 0.0, "fatigue": 0.0, "form": 0.0, "load": 0}

    def at(days_ago):
        return s.get((today - timedelta(days=days_ago)).isoformat(), zero)

    last7, prev7 = _window(acts, today, 7, 0), _window(acts, today, 14, 7)
    last28, prev28 = _window(acts, today, 28, 0), _window(acts, today, 56, 28)

    def change(days_ago):  # pre-computed so the LLM never has to do arithmetic (it gets signs wrong)
        then = at(days_ago)
        return {k: f"{k} {'up' if at(0)[k] > then[k] else 'down' if at(0)[k] < then[k] else 'unchanged'} "
                   f"{abs(at(0)[k] - then[k]):.1f} ({then[k]} -> {at(0)[k]})" for k in ("fitness", "fatigue", "form")}

    return {
        "today": at(0), "yesterday": at(1), "week_ago": at(7), "four_weeks_ago": at(28),
        "change_vs_yesterday": change(1), "change_vs_week_ago": change(7), "change_vs_four_weeks_ago": change(28),
        "km_last_7_days": round(sum(a["km"] for a in last7), 1),
        "km_previous_7_days": round(sum(a["km"] for a in prev7), 1),
        "runs_last_7_days": len(last7),
        "longest_run_last_28_days_km": round(max((a["km"] for a in last28), default=0), 1),
        "metres_per_heartbeat_last_28_days": _efficiency(last28),
        "metres_per_heartbeat_previous_28_days": _efficiency(prev28),
    }
