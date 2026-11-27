"""Training sessions: types, text (EN/ID) and how each is checked against Strava activities. Pure, no I/O.

A plan day holds a list of sessions, e.g. [{"type": "SBW", "rounds": 2}, {"type": "EW", "minutes": 30, "hr_max": 132}].
Optional fields: minutes, km, hr_max, pace (s/km), run_min / walk_min (run-walk split), reps, rounds,
tempo_km, warmup (index into WARMUPS), note (free text from an imported plan; shown instead of generated text)."""
from .i18n import plan_text

RUN_TYPES = ("Run", "TrailRun", "VirtualRun")
WALK_TYPES = ("Walk", "Hike")
STRENGTH_TYPES = ("WeightTraining", "Workout", "Crossfit", "Yoga", "Pilates")
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
    return LABELS.get(s["type"], (s["type"], s["type"]))[lang == "id"]


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


def _t(en: str, id_: str) -> dict:
    return {"en": en, "id": id_}


def check(s: dict, acts: list[dict], past: bool, max_hr: float) -> dict:
    """{'state': done|partial|missed|unverified|None, 'en': ..., 'id': ...} for one planned session.
    acts: that day's activity summaries ({type, km, moving_min, avg_hr, max_hr, km_splits, hard_blocks})."""
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
    if t == "TEMPO" and s.get("pace") and main.get("km_splits"):
        def secs(p):
            mm, ss = p.split("/")[0].split(":")
            return int(mm) * 60 + int(ss)
        fast = sum(1 for p in main["km_splits"] if secs(p) <= s["pace"] + 10)
        if fast < max(1, round(0.8 * s.get("tempo_km", 2))):
            return {"state": "partial", "en": got["en"] + f" — only {fast} km near tempo pace.",
                    "id": got["id"] + f" — hanya {fast} km mendekati pace tempo."}
    if t == "INT" and main.get("max_hr") and main["max_hr"] < 0.88 * max_hr:
        return {"state": "partial", "en": got["en"] + " — no hard efforts seen in heart rate.",
                "id": got["id"] + " — tidak terlihat upaya berat di detak jantung."}
    if t == "N4X4":
        blocks = main.get("hard_blocks")
        if blocks is None:
            return {"state": "done", "en": got["en"] + " — no heart-rate data to check the 4 hard blocks.",
                    "id": got["id"] + " — tidak ada data HR untuk cek 4 blok berat."}
        if blocks < 4:
            return {"state": "partial", "en": got["en"] + f" — {blocks} of 4 hard blocks reached 85% max HR.",
                    "id": got["id"] + f" — {blocks} dari 4 blok berat mencapai 85% HR maks."}
        return {"state": "done", "en": got["en"] + " — 4 hard blocks ✓", "id": got["id"] + " — 4 blok berat ✓"}
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
