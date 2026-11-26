"""Pure training-plan generator. No I/O: give it stats + event, get a list of days back."""
from dataclasses import dataclass, asdict
from datetime import date, timedelta

DISTANCES_KM = {"5k": 5.0, "10k": 10.0, "half": 21.0975, "marathon": 42.195}
# Peak weekly km and taper weeks per distance.
PEAK_KM = {"5k": 35, "10k": 45, "half": 55, "marathon": 70}
TAPER_WEEKS = {"5k": 1, "10k": 1, "half": 2, "marathon": 3}
# Long run cap as share of race distance (marathon long run caps ~32 km).
LONG_CAP_KM = {"5k": 12, "10k": 16, "half": 21, "marathon": 32}
# Which weekdays (Mon=0) to run, by runs/week. Long run is always the last listed day.
RUN_DAYS = {
    3: [1, 3, 6],
    4: [1, 3, 4, 6],
    5: [0, 1, 3, 4, 6],
    6: [0, 1, 2, 3, 4, 6],
}


@dataclass
class Stats:
    weekly_km: float        # avg km/week over last 4 weeks
    longest_km: float       # longest run in last 12 weeks
    easy_pace_s: float      # typical pace, seconds per km


@dataclass
class Day:
    date: str
    kind: str               # rest | easy | long | intervals | tempo | race
    km: float
    detail: str


def fmt_pace(s: float) -> str:
    s = int(round(s))
    return f"{s // 60}:{s % 60:02d}/km"


def paces(stats: Stats, distance: str, goal_s: int | None) -> dict:
    """Return easy/tempo/interval/race paces in s/km."""
    if goal_s:
        race = goal_s / DISTANCES_KM[distance]
        easy = race + {"5k": 90, "10k": 75, "half": 60, "marathon": 45}[distance]
    else:
        easy = stats.easy_pace_s
        race = easy - {"5k": 75, "10k": 60, "half": 45, "marathon": 30}[distance]
    return {"easy": easy, "tempo": easy - 50, "interval": easy - 80, "race": race}


def weekly_targets(start_km: float, peak_km: float, weeks: int, taper: int) -> list[float]:
    """Volume per week: +10%/wk with every 4th week a cutback, then taper."""
    build_weeks = max(weeks - taper, 0)
    vols, v = [], start_km
    for i in range(build_weeks):
        if (i + 1) % 4 == 0:
            vols.append(round(v * 0.8, 1))  # cutback, don't advance v
        else:
            v = min(v * 1.10, peak_km) if i else v
            vols.append(round(v, 1))
    last = max(vols) if vols else start_km  # taper from peak, not from a cutback week
    for t in range(min(taper, weeks)):
        vols.append(round(last * (0.75 - 0.2 * t), 1))
    return vols


def build_plan(stats: Stats, distance: str, event: date, runs_per_week: int,
               goal_s: int | None = None, today: date | None = None) -> list[Day]:
    today = today or date.today()
    if distance not in DISTANCES_KM:
        raise ValueError("unknown distance")
    if event <= today:
        raise ValueError("event must be in the future")
    runs_per_week = min(max(runs_per_week, 3), 6)

    # Plan starts on the Monday of the current week; past days are dropped at the end.
    start = today - timedelta(days=today.weekday())
    weeks = (event - start).days // 7 + 1
    start_km = max(stats.weekly_km, 10.0)
    peak = max(PEAK_KM[distance], start_km)
    vols = weekly_targets(start_km, peak, weeks, TAPER_WEEKS[distance])
    p = paces(stats, distance, goal_s)
    run_days = RUN_DAYS[runs_per_week]
    long_cap = LONG_CAP_KM[distance]
    longest = max(stats.longest_km, 5.0)

    days: list[Day] = []
    for w, vol in enumerate(vols):
        # Long run ~35% of week, grows ≤ 1.5 km/week from current longest, capped per distance.
        long_km = round(min(vol * 0.35, longest + 1.5 * (w + 1), long_cap), 1)
        quality_km = round(vol * 0.2, 1)
        n_easy = runs_per_week - 2
        easy_km = round(max((vol - long_km - quality_km) / n_easy, 3.0), 1) if n_easy else 0
        quality = "intervals" if w % 2 == 0 else "tempo"
        for dow in range(7):
            d = start + timedelta(days=w * 7 + dow)
            if d > event:
                break
            if d == event:
                days.append(Day(d.isoformat(), "race", DISTANCES_KM[distance],
                                f"Race day! Target {fmt_pace(p['race'])}"))
                break
            if dow not in run_days:
                days.append(Day(d.isoformat(), "rest", 0, "Rest or light mobility"))
            elif dow == run_days[-1]:
                days.append(Day(d.isoformat(), "long", long_km,
                                f"Long run, conversational at {fmt_pace(p['easy'])}"))
            elif dow == run_days[0]:
                if quality == "intervals":
                    detail = (f"Warm up 2 km, 6×800 m at {fmt_pace(p['interval'])} "
                              f"with 400 m jog, cool down")
                else:
                    detail = f"Warm up 2 km, {max(quality_km - 3, 2):.0f} km at {fmt_pace(p['tempo'])}, cool down"
                days.append(Day(d.isoformat(), quality, quality_km, detail))
            else:
                days.append(Day(d.isoformat(), "easy", easy_km, f"Easy at {fmt_pace(p['easy'])}"))

    return [d for d in days if d.date >= today.isoformat()]


def plan_to_dicts(days: list[Day]) -> list[dict]:
    return [asdict(d) for d in days]


def day_status(day: dict, today: str) -> str | None:
    """done / partial / extra (ran on a rest day) / missed / None (upcoming or rest)."""
    runs = day.get("runs") or {}
    if runs:
        if day["kind"] == "rest":
            return "extra"
        km = sum(r["km"] for r in runs.values())
        return "done" if km >= 0.8 * day["km"] or day["kind"] == "race" else "partial"
    if day["date"] < today and day["kind"] != "rest":
        return "missed"
    return None
