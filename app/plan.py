"""Pure training-plan generator. No I/O: give it stats + event, get a list of days back."""
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta

from .sessions import describe, kind_of

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
    kind: str               # main session, for colour: rest|walk|runwalk|easy|long|tempo|intervals|n4x4|strength|race
    km: float
    detail: str             # English text of all sessions (used by the coach)
    sessions: list = field(default_factory=list)


def make_day(d: str, sessions: list[dict]) -> Day:
    km = round(sum(x.get("km") or 0 for x in sessions if x["type"] != "STRIDES"), 1)
    return Day(d, kind_of(sessions), km, "; ".join(describe(x) for x in sessions), sessions)


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

    # Beginners (low volume or slow easy pace) start with run-walk and Norwegian 4x4 instead of track intervals.
    beginner = stats.weekly_km < 12 or stats.easy_pace_s > 450
    build_weeks = len(vols) - min(TAPER_WEEKS[distance], len(vols))
    long_dow = run_days[-1]
    rest_dows = [x for x in range(7) if x not in run_days and x != (long_dow - 1) % 7]
    easy_dows = [x for x in run_days if x not in (run_days[0], long_dow)]
    strength_dows = (rest_dows + easy_dows)[:2]  # 2x/week, on rest days first, never the day before the long run
    rnd5 = lambda x: max(20, int(5 * round(x / 5)))  # noqa: E731

    days: list[Day] = []
    for w, vol in enumerate(vols):
        phase = ("taper" if w >= build_weeks else "base" if w < max(2, build_weeks // 3)
                 else "peak" if w >= build_weeks - 3 else "build")
        wu = w % 3  # warm-up variation of the week
        # Long run ~35% of week, grows <= 1.5 km/week from current longest, capped per distance.
        long_km = round(min(vol * 0.35, longest + 1.5 * (w + 1), long_cap), 1)
        quality_km = round(vol * 0.2, 1)
        n_easy = runs_per_week - 2
        easy_km = round(max((vol - long_km - quality_km) / n_easy, 3.0), 1) if n_easy else 0
        quality = ("TEMPO" if phase == "taper" else "N4X4" if beginner else ["INT", "TEMPO", "N4X4"][w % 3])
        run_walk = beginner and phase == "base"
        rounds = {"base": 2, "build": 3, "peak": 2, "taper": 1}[phase]
        for dow in range(7):
            d = start + timedelta(days=w * 7 + dow)
            if d > event:
                break
            if d == event:
                days.append(make_day(d.isoformat(), [{"type": "RACE", "km": DISTANCES_KM[distance], "pace": p["race"]}]))
                break
            sess: list[dict] = []
            if dow == long_dow:
                long_var = {"base": "classic", "build": ["classic", "progression", "surges"][w % 3],
                            "peak": ["fast_finish", "race_pace", "classic"][w % 3], "taper": "classic"}[phase]
                sess.append({"type": "LRW", "km": long_km, "run_min": 4, "walk_min": 1, "warmup": wu} if run_walk else
                            {"type": "LONG", "km": long_km, "pace": p["easy"], "warmup": wu, "var": long_var})
            elif dow == run_days[0]:
                qvar = {"N4X4": "n4x4", "INT": ["track", "hiit", "pyramid", "fartlek", "sprints"][(w // 3) % 5],
                        "TEMPO": ["steady", "cruise", "progressive"][(w // 3) % 3]}[quality]
                sess.append({"type": quality, "km": quality_km, "warmup": wu, "var": qvar,
                             **({"minutes": 40} if quality == "N4X4" else
                                {"reps": 6, "pace": p["interval"]} if quality == "INT" else
                                {"tempo_km": max(round(quality_km) - 3, 2), "pace": p["tempo"]})})
            elif dow in run_days:
                sess.append({"type": "RW", "km": easy_km, "minutes": rnd5(easy_km * p["easy"] / 60),
                             "run_min": 2, "walk_min": 1, "warmup": wu} if run_walk else
                            {"type": "EASY", "km": easy_km, "pace": p["easy"], "warmup": wu,
                             "var": ("strides" if phase in ("build", "peak") and dow == easy_dows[-1] else
                                     "progression" if phase == "build" and w % 2 else "aerobic")})
            if dow in strength_dows and (event - d).days > 4:
                sess.append({"type": "SBW", "rounds": rounds})
            days.append(make_day(d.isoformat(), sess or [{"type": "REST"}]))

    return [d for d in days if d.date >= today.isoformat()]


def plan_to_dicts(days: list[Day]) -> list[dict]:
    return [asdict(d) for d in days]


QUALITY = ("intervals", "tempo", "n4x4")
EASY_DETAIL = "Easy, conversational effort"


def adapt(by_date: dict[str, dict], km_by_date: dict[str, float], today: str, form_tomorrow: float) -> list[str]:
    """Adjust upcoming days after what actually happened. Runs nightly; mutates by_date in place and
    returns what changed. Rules (deliberately conservative - never adds training):
      1. Long run missed yesterday -> moved to tomorrow unless another long run is today or within
         2 days after tomorrow;
         a hard session the day after it becomes easy. Otherwise it's dropped.
      2. Last week under 80% of plan -> this week's easy/long runs shortened (max 40% cut; a moved
         long run is kept whole).
      3. Very tired (form below -20) -> tomorrow's hard session becomes easy.
    Missed hard sessions are simply dropped (never doubled up); running more than planned changes nothing."""
    t = date.fromisoformat(today)
    tomorrow, yesterday = (t + timedelta(days=1)).isoformat(), (t - timedelta(days=1)).isoformat()
    changes: list[str] = []

    def strength(d):
        return [x for x in d.get("sessions") or [] if x["type"] == "SBW"]

    def easy_instead(d, label):
        change(d, label, kind="easy", detail=EASY_DETAIL,
               sessions=[{"type": "EASY", "km": d["km"], "note": EASY_DETAIL}] + strength(d))

    def change(d, label, **new):
        d.update(new)
        d["adjusted"] = label
        d.pop("why", None)  # coach note is rewritten for the new session
        changes.append(f"{d['date']}: {label}")

    y, tm = by_date.get(yesterday), by_date.get(tomorrow)
    if y and y["kind"] == "long" and not km_by_date.get(yesterday) and not y.get("moved") and not y.get("handled"):
        y["handled"] = "dropped"
        # no other long run/race today or within 2 days after tomorrow (no back-to-back long days)
        near = {(t + timedelta(days=i)).isoformat() for i in (0, 2, 3)}
        room = not any(by_date[k]["kind"] in ("long", "race") for k in near if k in by_date)
        if tm and tm["kind"] not in ("long", "race") and room:
            y["handled"] = "moved"
            runs = [x for x in y.get("sessions") or [{"type": "LONG", "km": y["km"], "note": y["detail"]}]
                    if x["type"] != "SBW"]
            change(tm, f"Long run moved here from {date.fromisoformat(yesterday):%a} (missed)",
                   kind="long", km=y["km"], detail=y["detail"], moved=True, sessions=runs + strength(tm))
            after = by_date.get((t + timedelta(days=2)).isoformat())
            if after and after["kind"] in QUALITY:
                easy_instead(after, "Easy instead of hard: the day after a long run")

    monday = t - timedelta(days=t.weekday())
    mon = by_date.get(monday.isoformat())
    prev = [by_date.get((monday - timedelta(days=i)).isoformat()) for i in range(1, 8)]
    if mon and not mon.get("week_checked") and all(prev):
        mon["week_checked"] = True
        planned = sum(d["km"] for d in prev)
        actual = sum(km_by_date.get(d["date"], 0) for d in prev)
        actual += sum(d["km"] for d in prev if d.get("handled") == "moved")  # carried over, not lost
        week = [d for k, d in by_date.items() if monday.isoformat() <= k <= (monday + timedelta(days=6)).isoformat()]
        total = sum(d["km"] for d in week)
        if planned and total and actual < 0.8 * planned:
            f = max(min(1.0, actual * 1.1 / total), 0.6)
            for d in week:
                if d["date"] > today and d["kind"] in ("easy", "long") and not d.get("moved") and f < 1:
                    km = max(round(d["km"] * f, 1), 3.0)
                    sess = [{**x, **({"km": round(x["km"] * km / d["km"], 1)} if x.get("km") else {}),
                             **({"minutes": max(15, round(x["minutes"] * km / d["km"]))} if x.get("minutes") else {})}
                            for x in d.get("sessions") or []]
                    change(d, f"Shorter: last week you ran {actual:.0f} of {planned:.0f} km", km=km,
                           **({"sessions": sess} if sess else {}))

    if form_tomorrow < -20 and tm and tm["kind"] in QUALITY:
        easy_instead(tm, f"Easy instead of {tm['kind']}: you're very tired (form {form_tomorrow:.0f})")
    return changes
