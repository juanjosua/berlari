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
    phase: str | None = None  # base | build1 | build2 | peak | taper


def make_day(d: str, sessions: list[dict], phase: str | None = None) -> Day:
    km = round(sum(x.get("km") or 0 for x in sessions if x["type"] != "STRIDES"), 1)
    return Day(d, kind_of(sessions), km, "; ".join(describe(x) for x in sessions), sessions, phase)


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
               goal_s: int | None = None, today: date | None = None, prefs: dict | None = None) -> list[Day]:
    """prefs: the athlete's own default variation per family, e.g. {"INT": "n4x4", "EASY": "runwalk"};
    it replaces the variation the plan would otherwise recommend for that phase."""
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

    def pick(family, recommended):
        return (prefs or {}).get(family) or recommended

    days: list[Day] = []
    for w, vol in enumerate(vols):
        base_end, peak_start = max(2, build_weeks // 3), build_weeks - 3
        phase = ("taper" if w >= build_weeks else "base" if w < base_end
                 else "peak" if w >= peak_start else "build")
        # the long build block is split in two so there's a checkpoint roughly every 6-8 weeks
        tag = "build1" if phase == "build" and w < (base_end + peak_start) // 2 else "build2" if phase == "build" else phase
        wu = w % 3  # warm-up variation of the week
        # Long run ~35% of week, grows <= 1.5 km/week from current longest, capped per distance.
        long_km = round(min(vol * 0.35, longest + 1.5 * (w + 1), long_cap), 1)
        quality_km = round(vol * 0.2, 1)
        n_easy = runs_per_week - 2
        easy_km = round(max((vol - long_km - quality_km) / n_easy, 3.0), 1) if n_easy else 0
        quality = "TEMPO" if phase == "taper" else "INT" if beginner else ["INT", "TEMPO", "INT"][w % 3]
        run_walk = beginner and phase == "base"
        rounds = {"base": 2, "build": 3, "peak": 2, "taper": 1}[phase]
        for dow in range(7):
            d = start + timedelta(days=w * 7 + dow)
            if d > event:
                break
            if d == event:
                days.append(make_day(d.isoformat(), [{"type": "RACE", "km": DISTANCES_KM[distance], "pace": p["race"]}],
                                     tag))
                break
            sess: list[dict] = []
            if dow == long_dow:
                long_var = ("walk_breaks" if run_walk else
                            {"base": "classic", "build": "classic", "peak": ["fast_finish", "classic"][w % 2],
                             "taper": "classic"}[phase])
                sess.append({"type": "LONG", "km": long_km, "pace": p["easy"], "warmup": wu,
                             "var": pick("LONG", long_var), "rec": long_var})
            elif dow == run_days[0]:
                if quality == "INT":
                    rec = "n4x4" if beginner else ["track", "fartlek", "n4x4"][(w // 3) % 3]
                    sess.append({"type": "INT", "km": quality_km, "minutes": 40, "warmup": wu,
                                 "pace": p["interval"], "var": pick("INT", rec), "rec": rec})
                else:
                    trec = ["steady", "cruise", "progressive"][(w // 3) % 3]
                    sess.append({"type": "TEMPO", "km": quality_km, "warmup": wu, "pace": p["tempo"],
                                 "tempo_km": max(round(quality_km) - 3, 2),
                                 "var": pick("TEMPO", trec), "rec": trec})
            elif dow in run_days:
                rec = ("runwalk" if run_walk else "strides" if phase in ("build", "peak") and dow == easy_dows[-1]
                       else "aerobic")
                var = pick("EASY", rec)
                sess.append({"type": "EASY", "km": easy_km, "pace": p["easy"], "warmup": wu, "var": var, "rec": rec,
                             **({"minutes": rnd5(easy_km * p["easy"] / 60)} if var == "runwalk" else {})})
            if dow in strength_dows and (event - d).days > 4:
                srec = ["classic", "single_leg", "core_hips"][w % 3]
                sess.append({"type": "SBW", "rounds": rounds,
                             "var": pick("SBW", srec), "rec": srec})
            days.append(make_day(d.isoformat(), sess or [{"type": "REST"}], tag))

    return [d for d in days if d.date >= today.isoformat()]


# --- Phases: goal, checkpoint, evaluation ---

PHASES = {
    "base": {"label": ("Base", "Fondasi"),
             "goal": ("Build the habit and your aerobic base: train consistently at easy effort so joints, tendons "
                      "and heart adapt. Speed doesn't matter yet.",
                      "Membangun kebiasaan dan dasar aerobik: latihan rutin di usaha santai agar sendi, tendon dan "
                      "jantung beradaptasi. Kecepatan belum penting.")},
    "build1": {"label": ("Build 1", "Membangun 1"),
               "goal": ("Start growing the long run and get used to one harder session a week, without new aches.",
                        "Mulai menambah jarak lari jauh dan terbiasa dengan satu sesi lebih berat per minggu, tanpa "
                        "keluhan nyeri baru.")},
    "build2": {"label": ("Build 2", "Membangun 2"),
               "goal": ("Keep growing the long run and handle tempo and interval sessions at the planned effort.",
                        "Terus menambah jarak lari jauh dan sanggup menjalani sesi tempo dan interval sesuai usaha "
                        "yang direncanakan.")},
    "peak": {"label": ("Peak", "Puncak"),
             "goal": ("Reach your longest runs and race-specific sessions: prove you can cover most of the race "
                      "distance comfortably.",
                      "Mencapai lari terjauh dan sesi khusus lomba: membuktikan kamu bisa menempuh sebagian besar "
                      "jarak lomba dengan nyaman.")},
    "taper": {"label": ("Taper", "Tapering"),
              "goal": ("Train less so you arrive at the start line fresh. Keep a little intensity, sleep well, "
                       "practise race-day routines.",
                       "Kurangi latihan agar tiba di garis start dalam kondisi segar. Pertahankan sedikit intensitas, "
                       "tidur cukup, latih rutinitas hari lomba.")},
}
PASS_RATIO = 0.75  # share of the phase's planned sessions that must be done (partly done counts half)


def plan_phases(days: list[dict]) -> list[dict]:
    """Consecutive phases with dates and their checkpoint: the phase's last long run (none for taper)."""
    out: list[dict] = []
    for d in days:
        ph = d.get("phase")
        if not ph:
            continue
        if not out or out[-1]["key"] != ph:
            out.append({"key": ph, "start": d["date"], "end": d["date"], "checkpoint": None, "target_km": None})
        out[-1]["end"] = d["date"]
        if ph != "taper":
            for x in d.get("sessions") or []:
                if x["type"] == "LONG":
                    out[-1]["checkpoint"], out[-1]["target_km"] = d["date"], x.get("km")
    return out


def evaluate_phase(ph: dict, days: list[dict]) -> dict:
    """days: the phase's plan days with 'sessions' and 'checks'. Pass = enough sessions done AND the
    checkpoint long run done as planned."""
    states = [c["state"] for d in days if ph["start"] <= d["date"] <= ph["end"]
              for c in d.get("checks", []) if c.get("state") in ("done", "partial", "missed")]
    score = sum(1 if x == "done" else 0.5 if x == "partial" else 0 for x in states)
    ratio = round(score / len(states), 2) if states else 0.0
    cp = next((d for d in days if d["date"] == ph["checkpoint"]), None)
    cp_state = next((c.get("state") for x, c in zip(cp["sessions"], cp["checks"]) if x["type"] == "LONG"), None) if cp else None
    return {"passed": ratio >= PASS_RATIO and cp_state == "done", "ratio": ratio, "checkpoint_state": cp_state,
            "sessions": len(states)}


ADJUST_LABEL = "Lighter: the previous phase goal wasn't reached"


def adjust_after_failed_phase(by_date: dict[str, dict], phase_key: str, after: str, factor: float = 0.85) -> int:
    """Make the next phase gentler: shorten running sessions and, for easy/long runs the athlete didn't pick
    themselves, switch to run-walk / walk breaks. Mutates by_date, returns how many days changed."""
    changed = 0
    for k, d in sorted(by_date.items()):
        if k <= after or d.get("phase") != phase_key:
            continue
        sess = d.get("sessions") or []
        hit = False
        for x in sess:
            if x["type"] in ("EASY", "LONG", "TEMPO", "INT"):
                if x.get("km"):
                    x["km"] = round(x["km"] * factor, 1)
                if x.get("minutes"):
                    x["minutes"] = max(15, round(x["minutes"] * factor))
                if not x.get("var_set") and x["type"] in ("EASY", "LONG"):
                    x["var"] = "runwalk" if x["type"] == "EASY" else "walk_breaks"
                hit = True
        if hit:
            d["km"] = round(sum(x.get("km") or 0 for x in sess), 1)
            d["detail"] = "; ".join(describe(x) for x in sess)
            d["adjusted"] = ADJUST_LABEL
            d.pop("why", None)
            changed += 1
    return changed


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


def checkpoint_text(ph: dict, lang: str = "en") -> str:
    from .i18n import fmt_date
    id_ = lang == "id"
    if not ph.get("checkpoint"):
        return ""
    day = fmt_date(ph["checkpoint"], "%a %d %b", lang)
    km = f" {ph['target_km']:g} km" if ph.get("target_km") else ""
    return (f"Checkpoint {day}: selesaikan lari jauh{km} sesuai rencana, dan minimal {PASS_RATIO:.0%} sesi di fase ini."
            if id_ else f"Checkpoint {day}: complete the{km} long run as planned, and at least {PASS_RATIO:.0%} "
                        f"of this phase's sessions.")


def phase_message(res: dict, lang: str = "en") -> str:
    """Plain-language verdict of a phase checkpoint and what happens next."""
    id_ = lang == "id"
    pct = round(res["ratio"] * 100)
    label = PHASES[res["phase"]]["label"][id_]
    nxt = PHASES[res["next"]]["label"][id_] if res.get("next") else None
    if res["passed"]:
        if id_:
            return (f"Target {label} tercapai: {pct}% sesi selesai dan lari jauh checkpoint tuntas."
                    + (f" {nxt} berjalan sesuai rencana." if nxt else ""))
        return (f"{label} goal reached: {pct}% of sessions done and the checkpoint long run completed."
                + (f" {nxt} continues as planned." if nxt else ""))
    cp = res.get("checkpoint_state")
    if id_:
        why = ([f"baru {pct}% sesi selesai (perlu {PASS_RATIO:.0%})"] if res["ratio"] < PASS_RATIO else []) + \
              ([{"partial": "lari jauh checkpoint hanya sebagian", "missed": "lari jauh checkpoint terlewat"}
                .get(cp, "lari jauh checkpoint tidak tercatat")] if cp != "done" else [])
        msg = f"Target {label} belum tercapai: {' dan '.join(why)}."
        if res.get("adjusted"):
            msg += (f" {nxt} dibuat sekitar 15% lebih ringan, dan lari santai serta lari jauh diganti ke lari-jalan dan "
                    f"jeda jalan (kecuali yang kamu pilih sendiri), agar kamu bisa mengejar dengan aman tanpa risiko "
                    f"cedera. Fokus: jalani setiap sesi santai, walau singkat, sebelum menambah kecepatan.")
        elif res.get("next") == "taper":
            msg += (" Jangan mencoba mengejar sekarang. Mulai lomba dengan konservatif dan pakai jeda jalan sejak km "
                    "pertama; itu cara paling aman untuk finis.")
        return msg
    why = ([f"only {pct}% of sessions done (needed {PASS_RATIO:.0%})"] if res["ratio"] < PASS_RATIO else []) + \
          ([{"partial": "the checkpoint long run was only partly done", "missed": "the checkpoint long run was missed"}
            .get(cp, "the checkpoint long run wasn't recorded")] if cp != "done" else [])
    msg = f"{label} goal not reached: {' and '.join(why)}."
    if res.get("adjusted"):
        msg += (f" {nxt} has been made about 15% lighter, and easy and long runs switch to run-walk and walk breaks "
                f"(unless you chose them yourself), so you can catch up without risking injury. Focus on doing every "
                f"easy session, even short ones, before adding speed.")
    elif res.get("next") == "taper":
        msg += (" Don't try to make up for it now. Start the race conservatively and use walk breaks from the first "
                "km; it's the safest way to finish.")
    return msg
