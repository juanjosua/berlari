"""Training sessions: types, text (EN/ID) and how each is checked against Strava activities. Pure, no I/O.

A plan day holds a list of sessions, e.g. [{"type": "SBW", "rounds": 2}, {"type": "EW", "minutes": 30, "hr_max": 132}].
Optional fields: minutes, km, hr_max, pace (s/km), run_min / walk_min (run-walk split), reps, rounds,
tempo_km, warmup (index into WARMUPS), note (free text from an imported plan; shown instead of generated text)."""
from .i18n import plan_text

RUN_TYPES = ("Run", "TrailRun", "VirtualRun")
WALK_TYPES = ("Walk", "Hike")
STRENGTH_TYPES = ("WeightTraining", "Crossfit")  # not "Workout": too generic (padel, classes...)
ACTIVITY_TYPES = RUN_TYPES + WALK_TYPES + STRENGTH_TYPES

LABELS = {  # type: (English, Indonesian)
    "EW": ("Easy walk", "Jalan cepat santai"), "RW": ("Run-walk", "Lari-jalan"),
    "EASY": ("Easy run", "Lari santai"), "LONG": ("Long run", "Lari jauh"),
    "LRW": ("Long run-walk", "Lari-jalan jauh"), "TEMPO": ("Tempo run", "Lari tempo"),
    "INT": ("Intervals", "Interval"), "N4X4": ("Norwegian 4x4", "Norwegian 4x4"),
    "STRIDES": ("Strides", "Strides"), "SBW": ("Strength (bodyweight)", "Strength (tanpa alat)"),
    "RACE": ("Race", "Lomba"), "REST": ("Rest", "Istirahat"),
}
# Day colour/kind from its main session (first match wins).
KIND_ORDER = [("RACE", "race"), ("LONG", "long"), ("LRW", "long"), ("N4X4", "n4x4"), ("INT", "intervals"),
              ("TEMPO", "tempo"), ("RW", "runwalk"), ("EASY", "easy"), ("EW", "walk"), ("SBW", "strength")]
RUNNING = {"RW", "EASY", "LONG", "LRW", "TEMPO", "INT", "N4X4", "RACE"}
LEGACY = {"easy": "EASY", "long": "LONG", "tempo": "TEMPO", "intervals": "INT", "race": "RACE", "rest": "REST"}

WARMUPS = [  # rotated week by week so warm-ups vary
    ("5 min easy jog/walk, then leg swings, A-skips and high knees",
     "5 menit jogging/jalan santai, lalu leg swing, A-skip dan high knees"),
    ("5 min brisk walk, then hip circles, walking lunges and butt kicks",
     "5 menit jalan cepat, lalu putar pinggul, walking lunge dan butt kick"),
    ("5 min easy jog, then ankle hops, side shuffles and carioca",
     "5 menit jogging santai, lalu lompat kecil, side shuffle dan carioca"),
]
SBW_MOVES = ("glute bridge, squat, calf raise, reverse lunge, plank",
             "glute bridge, squat, calf raise, reverse lunge, plank")


def kind_of(sessions: list[dict]) -> str:
    types = {s["type"] for s in sessions}
    return next((k for t, k in KIND_ORDER if t in types), "rest")


def from_legacy(day: dict) -> list[dict]:
    """Plans created before sessions existed: one session from kind/km/detail."""
    return [{"type": LEGACY.get(day["kind"], "REST"), "km": day.get("km") or None, "note": day.get("detail")}]


def _p(s):  # pace text
    from .plan import fmt_pace
    return fmt_pace(s["pace"]) if s.get("pace") else ""


def describe(s: dict, lang: str = "en") -> str:
    if s.get("note"):
        return plan_text(s["note"], lang)
    id_ = lang == "id"
    t, m, km = s["type"], s.get("minutes"), s.get("km")
    hr = f", HR {'di bawah' if id_ else 'under'} {s['hr_max']} bpm" if s.get("hr_max") else ""
    if t == "EW":
        return (f"Jalan cepat {m} menit{hr}" if id_ else f"Brisk walk {m} min{hr}")
    if t in ("RW", "LRW"):
        amount = f"{m} {'menit' if id_ else 'min'}" if m else f"{km:g} km"
        split = (f": jogging {s['run_min']:g} menit / jalan {s['walk_min']:g} menit" if id_ else
                 f": {s['run_min']:g} min jog / {s['walk_min']:g} min walk") if s.get("run_min") else ""
        return (f"Lari-jalan {amount}{split}{hr}" if id_ else f"Run-walk {amount}{split}{hr}")
    if t == "EASY":
        amount = f"{km:g} km" if km else f"{m} {'menit' if id_ else 'min'}"
        return (f"{amount} santai di {_p(s)}{hr}" if id_ else f"{amount} easy at {_p(s)}{hr}")
    if t == "LONG":
        breaks = (", jalan 30–60 detik tiap 2 km" if id_ else ", walk 30–60 s every 2 km") if s.get("walk_breaks") else ""
        return (f"{km:g} km pace santai (masih bisa ngobrol) di {_p(s)}{breaks}" if id_ else
                f"{km:g} km conversational at {_p(s)}{breaks}")
    if t == "TEMPO":
        return (f"Pemanasan 2 km, {s.get('tempo_km', 2):g} km di {_p(s)}, lalu pendinginan" if id_ else
                f"2 km warm-up, {s.get('tempo_km', 2):g} km at {_p(s)}, cool down")
    if t == "INT":
        return (f"Pemanasan 2 km, {s.get('reps', 6)}×800 m di {_p(s)} dengan jogging 400 m, lalu pendinginan" if id_
                else f"2 km warm-up, {s.get('reps', 6)}×800 m at {_p(s)} with 400 m jog, cool down")
    if t == "N4X4":
        return ("4 × 4 menit berat (85–95% HR maks), 3 menit santai di antaranya, lalu jalan santai 10 menit" if id_
                else "4 × 4 min hard (85–95% of max HR), 3 min easy between, then 10 min cool-down walk")
    if t == "STRIDES":
        return (f"{s.get('reps', 4)} × 20 detik lari mengalir cepat (bukan sprint)" if id_ else
                f"{s.get('reps', 4)} × 20 s fast, relaxed strides (not a sprint)")
    if t == "SBW":
        r = s.get("rounds", 2)
        return (f"{r} putaran: {SBW_MOVES[1]}" if id_ else f"{r} rounds: {SBW_MOVES[0]}")
    if t == "RACE":
        return (f"Hari lomba! Target {_p(s)}" if id_ else f"Race day! Target {_p(s)}")
    return "Istirahat atau mobilitas ringan" if id_ else "Rest or light mobility"


def label(s: dict, lang: str = "en") -> str:
    t = "INT" if s["type"] == "N4X4" and s.get("var") not in (None, "n4x4") else s["type"]  # swapped to another interval
    return LABELS.get(t, (t, t))[lang == "id"]


def warmup(s: dict, lang: str = "en") -> str:
    if s.get("warmup") is None:
        return ""
    return ("Pemanasan: " if lang == "id" else "Warm-up: ") + WARMUPS[s["warmup"] % len(WARMUPS)][lang == "id"]


def hard_blocks(hr: list[float], secs: list[float], threshold: float, min_s: int = 180, gap: int = 10) -> int:
    """Count stretches of at least min_s seconds with heart rate at/above threshold (Norwegian 4x4 check).
    Dips shorter than `gap` seconds don't break a block (HR sensors drop out)."""
    blocks, start, last = 0, None, None
    for h, t in zip(hr, secs):
        if h < threshold:
            continue
        if start is None or t - last > gap:
            if start is not None:
                blocks += (last - start) >= min_s
            start = t
        last = t
    if start is not None:
        blocks += (last - start) >= min_s
    return blocks


def runs(flags: list[bool], step: int = 5, gap: int = 10) -> list[int]:
    """Durations (s) of stretches where flags are True in a 5-second series; dips of <= gap s are bridged."""
    out, start, last = [], None, None
    for i, f in enumerate(flags):
        if not f:
            continue
        if start is None or (i - last) * step > gap + step:
            if start is not None:
                out.append((last - start + 1) * step)
            start = i
        last = i
    if start is not None:
        out.append((last - start + 1) * step)
    return out


# Variations per family. Only ones whose structure shows up in Strava's speed/HR stream are listed.
VARIATIONS = {
    "INT": [
        ("track", ("Classic reps", "Repetisi klasik"),
         ("6 × 800 m hard (about 3–4 min each), 2–3 min easy jog between",
          "6 × 800 m cepat (sekitar 3–4 menit tiap rep), jogging santai 2–3 menit di antaranya")),
        ("hiit", ("HIIT 30/30", "HIIT 30/30"),
         ("12 × 30 s fast / 30 s easy jog", "12 × 30 detik cepat / 30 detik jogging santai")),
        ("sprints", ("Sprint intervals", "Sprint interval"),
         ("8 × 20 s near-max sprint, 2–3 min walk or jog to recover",
          "8 × 20 detik sprint hampir maksimal, pemulihan jalan/jogging 2–3 menit")),
        ("pyramid", ("Pyramid 1-2-3-2-1", "Piramida 1-2-3-2-1"),
         ("Hard for 1, 2, 3, 2, 1 min with the same time easy after each",
          "Cepat 1, 2, 3, 2, 1 menit, lalu santai dengan durasi sama setelah tiap blok")),
        ("fartlek", ("Fartlek", "Fartlek"),
         ("Easy run with 8 surges of 1–2 min at 5K–10K effort, whenever you like",
          "Lari santai dengan 8 akselerasi 1–2 menit di effort 5K–10K, kapan saja")),
        ("n4x4", ("Norwegian 4x4", "Norwegian 4x4"),
         ("4 × 4 min at 85–95% of max HR, 3 min easy between", "4 × 4 menit di 85–95% HR maks, 3 menit santai di antaranya")),
    ],
    "TEMPO": [
        ("steady", ("Steady tempo", "Tempo stabil"),
         ("20–30 min non-stop at tempo pace, comfortably hard", "20–30 menit nonstop di pace tempo, berat tapi terkendali")),
        ("cruise", ("Cruise intervals", "Cruise interval"),
         ("4–5 × 1 km at tempo pace with 60 s jog between", "4–5 × 1 km di pace tempo dengan jogging 60 detik di antaranya")),
        ("progressive", ("Progressive tempo", "Tempo progresif"),
         ("Start easy and speed up; last 15 min at tempo pace or faster",
          "Mulai santai lalu makin cepat; 15 menit terakhir di pace tempo atau lebih cepat")),
    ],
    "EASY": [
        ("aerobic", ("Steady aerobic", "Aerobik stabil"),
         ("Conversational the whole way, heart rate under 75% of max", "Pace ngobrol sepanjang lari, HR di bawah 75% maks")),
        ("recovery", ("Recovery run", "Lari pemulihan"),
         ("20–40 min, slower than easy pace, heart rate under 72% of max",
          "20–40 menit, lebih pelan dari pace santai, HR di bawah 72% maks")),
        ("strides", ("Easy + strides", "Santai + strides"),
         ("Easy run, then 6 × 20 s fast, relaxed strides at the end", "Lari santai, lalu 6 × 20 detik strides cepat dan rileks di akhir")),
        ("progression", ("Progression easy run", "Lari santai progresif"),
         ("Start very easy and drift up to the top of easy pace by the end",
          "Mulai sangat santai lalu naik perlahan ke batas atas pace santai di akhir")),
        ("trail", ("Trail / soft surface", "Trail / permukaan lunak"),
         ("Easy effort on trail or grass; go by heart rate, not pace",
          "Effort santai di trail atau rumput; patokan HR, bukan pace")),
    ],
    "LONG": [
        ("classic", ("Classic easy long run", "Lari jauh santai klasik"),
         ("Conversational the whole way, heart rate under 78% of max", "Pace ngobrol sepanjang lari, HR di bawah 78% maks")),
        ("progression", ("Progression long run", "Lari jauh progresif"),
         ("Start easy and speed up every few km; last quarter clearly faster",
          "Mulai santai dan makin cepat tiap beberapa km; seperempat akhir jelas lebih cepat")),
        ("fast_finish", ("Fast finish", "Fast finish"),
         ("Easy, then the last 15–20 min at tempo pace", "Santai, lalu 15–20 menit terakhir di pace tempo")),
        ("race_pace", ("Race-pace blocks", "Blok pace lomba"),
         ("Easy with 2 × 15 min at goal race pace in the second half",
          "Santai dengan 2 × 15 menit di pace target lomba pada paruh kedua")),
        ("surges", ("Long run with surges", "Lari jauh dengan akselerasi"),
         ("Easy with 6 pickups of 1–2 min at 10K effort", "Santai dengan 6 akselerasi 1–2 menit di effort 10K")),
        ("hilly", ("Hilly / trail long run", "Lari jauh berbukit / trail"),
         ("Rolling or trail route by effort, at least 10 m of climb per km",
          "Rute berbukit atau trail dengan patokan effort, minimal 10 m tanjakan per km")),
    ],
}
FAMILY = {"INT": "INT", "N4X4": "INT", "TEMPO": "TEMPO", "EASY": "EASY", "LONG": "LONG"}
DEFAULT_VAR = {"INT": "track", "N4X4": "n4x4", "TEMPO": "steady", "EASY": "aerobic", "LONG": "classic"}


def variations(s: dict) -> list:
    return VARIATIONS.get(FAMILY.get(s["type"], ""), [])


def variation(s: dict) -> tuple | None:
    """The chosen (or default) variation of a session, or None if its type has none."""
    vid = s.get("var") or DEFAULT_VAR.get(s["type"])
    return next((v for v in variations(s) if v[0] == vid), None)


def _mean(xs):
    return sum(xs) / len(xs) if xs else 0


def check_variation(vid: str, a: dict, max_hr: float, paces: dict) -> dict | None:
    """None if the activity matches the variation, else {'state', 'en', 'id'} explaining what was off."""
    st = a.get("stream") or {}
    v, hr = st.get("v") or [], st.get("hr") or []
    avg, n = a.get("avg_hr"), len(v)
    moving = [x for x in v if x > 0.5]
    med = sorted(moving)[len(moving) // 2] if moving else 0
    tempo_v = 1000 / paces["tempo"] if paces.get("tempo") else 0
    race_v = 1000 / paces["race"] if paces.get("race") else 0

    def bad(state, en, id_):
        return {"state": state, "en": en, "id": id_}

    def fast(mult, lo, hi, part=None):
        xs = v if part is None else v[int(n * part):]
        return [d for d in runs([x >= mult * med for x in xs]) if lo <= d <= hi]

    # checks that need only heart rate or summary numbers
    if vid == "n4x4":
        blocks = sum(d >= 180 for d in runs([h >= 0.85 * max_hr for h in hr])) if hr else a.get("hard_blocks")
        if blocks is None:
            return bad("done", "No heart-rate data to check the 4 hard blocks.", "Tidak ada data HR untuk cek 4 blok berat.")
        if blocks < 4:
            return bad("partial", f"{blocks} of 4 hard blocks reached 85% of max HR.",
                       f"{blocks} dari 4 blok berat mencapai 85% HR maks.")
        return None
    if vid in ("aerobic", "classic", "recovery"):
        cap = {"aerobic": 0.75, "classic": 0.78, "recovery": 0.72}[vid]
        if avg and avg > cap * max_hr + 2:
            return bad("partial", f"Avg HR {avg} is above {cap:.0%} of max ({cap * max_hr:.0f}): too hard for this run.",
                       f"Rata-rata HR {avg} di atas {cap:.0%} maks ({cap * max_hr:.0f}): terlalu berat untuk lari ini.")
        if vid == "recovery" and a.get("moving_min", 0) > 50:
            return bad("partial", "Longer than a recovery run (over 50 min).", "Lebih lama dari lari pemulihan (lebih dari 50 menit).")
        return None
    if vid in ("trail", "hilly"):
        elev = (a.get("elev_gain_m") or 0) / max(a.get("km") or 1, 0.1)
        if a.get("type") != "TrailRun" and elev < (10 if vid == "hilly" else 6):
            return bad("partial", f"Looks like flat road ({elev:.0f} m climb per km).",
                       f"Sepertinya jalan datar ({elev:.0f} m tanjakan per km).")
        return None
    # the rest need the speed stream
    if not v:
        return bad("done", "Structure can't be checked: no GPS speed data for this run.",
                   "Struktur tidak bisa dicek: tidak ada data kecepatan GPS untuk lari ini.")
    if vid in ("track", "hiit", "sprints", "pyramid", "fartlek", "surges"):
        need, got = {
            "track": (5, fast(1.12, 100, 330)), "hiit": (10, fast(1.12, 15, 75)), "sprints": (6, fast(1.3, 5, 40)),
            "pyramid": (4, fast(1.12, 40, 260)), "fartlek": (6, fast(1.12, 40, 160)), "surges": (5, fast(1.12, 40, 160)),
        }[vid]
        if len(got) < need or (vid == "pyramid" and max(got, default=0) < 140):
            return bad("partial", f"Found {len(got)} fast efforts; this session needs about {need}.",
                       f"Terdeteksi {len(got)} upaya cepat; sesi ini butuh sekitar {need}.")
    elif vid == "strides":
        got = fast(1.25, 5, 40, part=0.6)
        if len(got) < 4:
            return bad("partial", f"Found {len(got)} strides at the end; aim for 6.",
                       f"Terdeteksi {len(got)} strides di akhir; targetnya 6.")
    elif vid in ("steady", "cruise", "progressive", "fast_finish") and not tempo_v:
        return bad("done", "No tempo pace set, so pace can't be checked.", "Pace tempo belum ditentukan, jadi pace tidak bisa dicek.")
    elif vid == "steady":
        longest = max(runs([x >= 0.95 * tempo_v for x in v], gap=15), default=0)
        if longest < 960:
            return bad("partial", f"Longest stretch at tempo pace: {longest // 60} min (aim 20+).",
                       f"Bagian terpanjang di pace tempo: {longest // 60} menit (target 20+).")
    elif vid == "cruise":
        got = [d for d in runs([x >= 0.95 * tempo_v for x in v]) if 150 <= d <= 600]
        if len(got) < 4:
            return bad("partial", f"Found {len(got)} tempo reps; aim for 4–5.", f"Terdeteksi {len(got)} rep tempo; targetnya 4–5.")
    elif vid in ("progressive", "fast_finish"):
        last = _mean(v[-180:])  # last 15 min
        if last < 0.95 * tempo_v or (vid == "progressive" and last <= _mean(v[: n // 3])):
            return bad("partial", "The last 15 min weren't at tempo pace.", "15 menit terakhir belum di pace tempo.")
    elif vid == "progression":
        a_, b_ = (_mean(v[: n // 3]), _mean(v[-(n // 3):])) if a.get("km", 0) < 15 else (_mean(v[: n // 2]), _mean(v[-(n // 4):]))
        if b_ < 1.04 * a_:
            return bad("partial", "Pace didn't build up toward the end.", "Pace tidak meningkat menjelang akhir.")
    elif vid == "race_pace" and race_v:
        got = [d for d in runs([0.94 * race_v <= x <= 1.08 * race_v for x in v], gap=15) if d >= 600]
        if len(got) < 2:
            return bad("partial", f"Found {len(got)} blocks of 10+ min at race pace; aim for 2.",
                       f"Terdeteksi {len(got)} blok 10+ menit di pace lomba; targetnya 2.")
    return None


def _t(en: str, id_: str) -> dict:
    return {"en": en, "id": id_}


def check(s: dict, acts: list[dict], past: bool, max_hr: float, paces: dict | None = None) -> dict:
    """{'state': done|partial|missed|unverified|None, 'en': ..., 'id': ...} for one planned session.
    acts: that day's activity summaries (+ optional 5-s "stream"); paces: plan paces in s/km (tempo, race)."""
    t = s["type"]
    if t == "REST":
        return {"state": None}
    if t in ("STRIDES", "SBW") and not past and not any(a.get("type") in STRENGTH_TYPES for a in acts):
        return {"state": None}  # nothing to say about a future day yet
    if t == "STRIDES":
        return {"state": "unverified", **_t("Strides can't be checked from Strava.",
                                            "Strides tidak bisa dicek dari Strava.")}
    if t == "SBW":
        st = [a for a in acts if a.get("type") in STRENGTH_TYPES]
        if st:
            mins = round(sum(a["moving_min"] for a in st))
            return {"state": "done", **_t(f"Strength logged: {mins} min.", f"Strength tercatat: {mins} menit.")}
        return {"state": "unverified", **_t("Log it on Strava as Weight Training to track it.",
                                            "Catat di Strava sebagai Weight Training agar terlacak.")}
    ok_types = WALK_TYPES if t == "EW" else RUN_TYPES + (WALK_TYPES if t in ("RW", "LRW") else ())
    mine = [a for a in acts if a.get("type", "Run") in ok_types]
    if not mine:
        return {"state": "missed" if past else None, **(_t("No matching activity on Strava.",
                                                           "Tidak ada aktivitas yang cocok di Strava.") if past else {})}
    mins = sum(a["moving_min"] for a in mine)
    km = sum(a["km"] for a in mine)
    main = max(mine, key=lambda a: a["moving_min"])
    avg = main.get("avg_hr")
    got = _t(f"{km:.1f} km, {mins:.0f} min" + (f", avg HR {avg}" if avg else ""),
             f"{km:.1f} km, {mins:.0f} menit" + (f", rata-rata HR {avg}" if avg else ""))
    if t == "RACE":
        return {"state": "done", **got}
    # amount: minutes or km target
    if s.get("minutes"):
        enough = mins >= 0.8 * s["minutes"]
    elif s.get("km"):
        enough = km >= 0.8 * s["km"]
    else:
        enough = True
    if not enough:
        return {"state": "partial", "en": got["en"] + " — shorter than planned.",
                "id": got["id"] + " — lebih pendek dari rencana."}
    if s.get("hr_max") and avg and avg > s["hr_max"] + 2:
        return {"state": "partial", "en": got["en"] + f" — above the {s['hr_max']} bpm cap; go easier next time.",
                "id": got["id"] + f" — di atas batas {s['hr_max']} bpm; lebih pelan lain kali."}
    var = variation(s)
    if var:
        off = check_variation(var[0], main, max_hr, paces or {})
        if off:
            return {"state": off["state"], "en": f"{got['en']} — {off['en']}", "id": f"{got['id']} — {off['id']}"}
        return {"state": "done", "en": f"{got['en']} — {var[1][0]} ✓", "id": f"{got['id']} — {var[1][1]} ✓"}
    return {"state": "done", **got}


def day_state(checks: list[dict], acts: list[dict], sessions: list[dict], past: bool) -> str | None:
    """Combine session checks: done / partial / missed / extra (trained on a rest day) / None."""
    states = [c["state"] for c in checks if c["state"] in ("done", "partial", "missed")]
    if not states:
        planned_rest = all(s["type"] in ("REST", "SBW", "STRIDES") for s in sessions)
        moved = any(a.get("type", "Run") in RUN_TYPES + WALK_TYPES for a in acts)
        return "extra" if planned_rest and moved and not any(s["type"] == "SBW" for s in sessions) else None
    if all(x == "done" for x in states):
        return "done"
    if all(x == "missed" for x in states):
        return "missed" if past else None
    return "partial"
