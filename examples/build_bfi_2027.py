"""Builds examples/bfi-run-2027-half-marathon.json: a 28-week run-walk + strength plan for the
BFI Run 2027 Half Marathon (30 May 2027, ICE BSD), transcribed day by day from the athlete's own PDF.
Run: python examples/build_bfi_2027.py   Then import: python -m app.import_plan <athlete_id> <json>"""
import json
from datetime import date, timedelta
from pathlib import Path

HR = 132
D = {}  # date -> sessions


def day(d: str, *sessions):
    D[d] = list(sessions)


def ew(m, note):
    return {"type": "EW", "minutes": m, "hr_max": HR, "note": note}


def rw(m, note, run=None, walk=None):
    return {"type": "RW", "minutes": m, "note": note, **({"run_min": run, "walk_min": walk} if run else {})}


def sbw(rounds, note):
    return {"type": "SBW", "rounds": rounds, "note": note}


N4 = {"type": "N4X4", "minutes": 40, "note": "Norwegian 4x4 + cool-down jalan santai 10–14 menit."}
REST = {"type": "REST", "note": "Istirahat penuh."}


def lrw(m, note):
    return {"type": "LRW", "minutes": m, "note": note}


def lr(km, note):
    return {"type": "LONG", "km": km, "walk_breaks": True, "note": note}


def strides(note="4x strides ringan (15–20 detik lari mengalir, bukan sprint)."):
    return {"type": "STRIDES", "reps": 4, "note": note}


# --- Fase 1: Fondasi & Adaptasi (26 Nov – 31 Des 2026) ---
day("2026-11-26", {"type": "REST", "note": "Pemulihan pasca sesi Norwegian 4x4 kemarin."})
day("2026-11-27", ew(40, "Jalan cepat 40 menit (HR < 132 bpm) + stretching betis & paha 5 menit."))
day("2026-11-28", sbw(2, "SBW 2 putaran (Glute Bridge, Chair Squat, Calf Raise, Plank)."), ew(30, "EW 30 menit (HR < 132 bpm)."))
day("2026-11-29", REST)
fase1 = {  # week Monday: (Mon EW, Fri EW, Sat EW minutes, Mon note, Fri note)
    "2026-11-30": (40, 45, 35, "Jalan cepat 40 menit (HR < 132 bpm).", "Jalan cepat 45 menit (HR < 132 bpm)."),
    "2026-12-07": (45, 45, 40, "Jalan cepat 45 menit (HR < 132 bpm).", "Jalan cepat 45 menit (HR < 132 bpm)."),
    "2026-12-14": (45, 45, 40, "Jalan cepat 45 menit (selingi jogging sangat pelan 30 detik tiap 5 menit bila kaki nyaman).",
                   "Jalan cepat 45–50 menit (selipkan jogging pelan 30 detik tiap 5 menit bila bebas nyeri sendi)."),
    "2026-12-21": (50, 45, 40, "Jalan cepat 50 menit (selipkan jogging pelan 30 detik tiap 5 menit).", "Jalan cepat 45 menit."),
}
for mon, (m1, m5, m6, n1, n5) in fase1.items():
    d0 = date.fromisoformat(mon)
    k = lambda i: (d0 + timedelta(days=i)).isoformat()  # noqa: E731
    day(k(0), ew(m1, n1))
    day(k(1), sbw(2, "SBW 2 putaran" + (" + mobility sendi pergelangan kaki & pinggul 10 menit." if mon == "2026-11-30" else ".")))
    day(k(2), N4)
    day(k(3), {"type": "REST", "note": "Istirahat penuh (jeda 48 jam pemulihan sendi)."} if mon == "2026-11-30" else REST)
    day(k(4), ew(m5, n5))
    day(k(5), sbw(2, "SBW 2 putaran."), ew(m6, f"EW {m6} menit (HR < 132 bpm)."))
    day(k(6), REST)
day("2026-12-28", ew(50, "Jalan cepat 50 menit (selipkan jogging pelan 30 detik tiap 4–5 menit)."))
day("2026-12-29", sbw(2, "SBW 2 putaran."))
day("2026-12-30", N4)
day("2026-12-31", {"type": "REST", "note": "Istirahat penuh atau jalan santai 20 menit."})

# --- Fase 2: Transisi Run-Walk & Ritme (1 – 31 Jan 2027) ---
day("2027-01-01", ew(40, "Jalan cepat 40 menit (HR < 132 bpm)."))
day("2027-01-02", sbw(3, "SBW 2–3 putaran (masukkan gerakan Reverse Lunge alternatif)."))
day("2027-01-03", REST)
fase2 = {  # Monday: (Mon RW, Fri RW, Sat long-session minutes, Sat note)
    "2027-01-04": (rw(40, "Run-Walk 40 menit (2 menit jogging pelan / 2 menit jalan cepat).", 2, 2),
                   rw(45, "Run-Walk 45 menit (2 menit jogging pelan / 2 menit jalan cepat).", 2, 2),
                   55, "Long Session 55 menit (jalan cepat + jogging santai 1 menit tiap 4 menit)."),
    "2027-01-11": (rw(45, "Run-Walk 45 menit (2 menit jogging pelan / 2 menit jalan cepat).", 2, 2),
                   rw(45, "Run-Walk 45 menit (2 menit jogging pelan / 1,5 menit jalan cepat).", 2, 1.5),
                   60, "Long Session 60 menit (kombinasi jogging santai & jalan cepat)."),
    "2027-01-18": (rw(45, "Run-Walk 45–50 menit (2,5 menit jogging pelan / 1,5 menit jalan cepat).", 2.5, 1.5),
                   rw(45, "Run-Walk 45 menit (2 menit jogging pelan / 1,5 menit jalan cepat).", 2, 1.5),
                   65, "Long Session 65 menit (jogging pelan & jalan cepat terkontrol)."),
    "2027-01-25": (rw(50, "Run-Walk 50 menit (3 menit jogging pelan / 1,5 menit jalan cepat).", 3, 1.5),
                   rw(45, "Run-Walk 45 menit (2,5 menit jogging pelan / 1,5 menit jalan cepat).", 2.5, 1.5),
                   70, "Long Session 70 menit (jogging pelan & jalan cepat)."),
}
for mon, (r1, r5, lm, ln) in fase2.items():
    d0 = date.fromisoformat(mon)
    k = lambda i: (d0 + timedelta(days=i)).isoformat()  # noqa: E731
    day(k(0), r1)
    day(k(1), sbw(3, "SBW 2–3 putaran" + (" (5 gerakan penuh)." if mon == "2027-01-04" else ".")))
    day(k(2), N4)
    day(k(3), REST)
    day(k(4), r5)
    day(k(5), sbw(3, "SBW 2–3 putaran."), lrw(lm, ln))
    day(k(6), REST)

# --- Fase 3: Membangun Basis & Pace Target (1 Feb – 28 Mar 2027) ---
fase3 = {  # Monday: (Mon note, Fri note, long km, long note, SBW Sat note)
    "2027-02-01": ("Run-Walk 50 menit (3 menit jogging pelan / 1 menit jalan cepat).",
                   "Run-Walk 45 menit (uji ritme jogging mendekati 8:15–8:30/km, jalan cepat 1 menit tiap 4–5 menit).",
                   8, "Long Run 8 km (selingi jalan cepat 30–60 detik tiap 2 km).", "SBW 3 putaran."),
    "2027-02-08": ("Run-Walk 50 menit.", "Run-Walk 45 menit.", 9, "Long Run 9 km (walk break 30–60 detik tiap 2 km).", "SBW 3 putaran."),
    "2027-02-15": ("Run-Walk 50 menit.", "Run-Walk 45 menit.", 10, "Long Run 10 km (walk break 30–60 detik tiap 2–2,5 km).", "SBW 3 putaran."),
    "2027-02-22": ("Run-Walk 50 menit.", "Run-Walk 45 menit.", 10,
                   "Long Run 10 km (Checkpoint evaluasi pace ~8:15–8:30/km & kondisi sendi).", "SBW 2 putaran ringan."),
    "2027-03-01": ("Run-Walk 50 menit.", "Run-Walk 45 menit.", 11, "Long Run 11 km (walk break 30–60 detik tiap 2,5 km).", "SBW 3 putaran."),
    "2027-03-08": ("Run-Walk 50 menit.", "Run-Walk 45 menit.", 12, "Long Run 12 km (walk break 30–60 detik tiap 2,5–3 km).", "SBW 3 putaran."),
    "2027-03-15": ("Run-Walk 50 menit.", "Run-Walk 45 menit.", 13, "Long Run 13 km.", "SBW 3 putaran."),
    "2027-03-22": ("Run-Walk 50 menit.", "Run-Walk 45 menit.", 14, "Long Run 14 km.", "SBW 3 putaran."),
}
for mon, (n1, n5, km, ln, sn) in fase3.items():
    d0 = date.fromisoformat(mon)
    k = lambda i: (d0 + timedelta(days=i)).isoformat()  # noqa: E731
    day(k(0), rw(50, n1, *((3, 1) if mon == "2027-02-01" else ())))
    day(k(1), sbw(3, "SBW 3 putaran."))
    day(k(2), N4)
    day(k(3), REST)
    day(k(4), rw(45, n5))
    day(k(5), sbw(2 if "ringan" in sn else 3, sn), lr(km, ln))
    day(k(6), REST)

# --- Fase 4: Puncak Jarak / Peak (29 Mar – 30 Apr 2027) ---
fase4 = {  # Monday: (long km, long note)
    "2027-03-29": (15, "Long Run 15 km (latih minum air/elektrolit tiap 30–40 menit)."),
    "2027-04-05": (16, "Long Run 16 km (latih hidrasi/elektrolit tiap 30–40 menit)."),
    "2027-04-12": (18, "Long Run 18 km (Peak jarak terjauh, simulasi nutrisi & ritme aman)."),
}
for mon, (km, ln) in fase4.items():
    d0 = date.fromisoformat(mon)
    k = lambda i: (d0 + timedelta(days=i)).isoformat()  # noqa: E731
    day(k(0), rw(45, "Run-Walk 45 menit."))
    day(k(1), sbw(2, "SBW 2 putaran."))
    day(k(2), N4)
    day(k(3), REST)
    day(k(4), rw(40, "Run-Walk 40 menit."), strides())
    day(k(5), sbw(2, "SBW 2 putaran."), lr(km, ln))
    day(k(6), REST)
day("2027-04-19", ew(40, "Easy Walk 40 menit (pemulihan aktif pasca peak 18 km)."))
day("2027-04-20", sbw(2, "SBW 2 putaran."))
day("2027-04-21", N4)
day("2027-04-22", REST)
day("2027-04-23", rw(40, "Run-Walk 40 menit."))
day("2027-04-24", sbw(2, "SBW 2 putaran."), lr(12, "Long Run 12 km (deload terkontrol agar sendi segar)."))
day("2027-04-25", REST)
day("2027-04-26", rw(45, "Run-Walk 45 menit."))
day("2027-04-27", sbw(2, "SBW 2 putaran."))
day("2027-04-28", N4)
day("2027-04-29", REST)
day("2027-04-30", rw(40, "Run-Walk 40 menit."))

# --- Fase 5: Tapering & Race Day (1 – 30 Mei 2027) ---
day("2027-05-01", sbw(2, "SBW 2 putaran."), lr(13, "Long Run 13 km."))
day("2027-05-02", REST)
day("2027-05-03", rw(40, "Run-Walk 40 menit."))
day("2027-05-04", sbw(2, "SBW 2 putaran."))
day("2027-05-05", N4)
day("2027-05-06", REST)
day("2027-05-07", rw(40, "Run-Walk 40 menit."))
day("2027-05-08", sbw(2, "SBW 2 putaran."), lr(12, "Long Run 12 km."))
day("2027-05-09", REST)
day("2027-05-10", rw(35, "Run-Walk 35–40 menit."))
day("2027-05-11", sbw(1, "SBW 1–2 putaran."))
day("2027-05-12", {**N4, "note": "Norwegian 4x4 terakhir (volume terjaga, fokus kualitas tanpa memaksa)."})
day("2027-05-13", REST)
day("2027-05-14", rw(35, "Run-Walk 35 menit."))
day("2027-05-15", lr(8, "Long Run 8–10 km santai."))
day("2027-05-16", REST)
day("2027-05-17", rw(30, "Run-Walk 30–35 menit."))
day("2027-05-18", sbw(1, "SBW 1 putaran ringan."))
day("2027-05-19", rw(30, "Run-Walk 30 menit (selingi 3x 30 detik jogging ritme target 8:00–8:15/km)."))
day("2027-05-20", REST)
day("2027-05-21", ew(25, "Easy Walk 25–30 menit."))
day("2027-05-22", ew(20, "Easy Walk 20 menit santai."))
day("2027-05-23", REST)
day("2027-05-24", rw(30, "Run-Walk 30 menit."), sbw(1, "SBW ringan 1 putaran."))
day("2027-05-25", REST)
day("2027-05-26", rw(25, "Run-Walk 25–30 menit (termasuk 3–4x 30 detik jogging ritme lomba)."))
day("2027-05-27", {"type": "REST", "note": "Istirahat penuh (cek sepatu, kaus kaki, BIB, dan perlengkapan lomba)."})
day("2027-05-28", ew(15, "Jalan santai 15–20 menit + peregangan ringan."))
day("2027-05-29", {"type": "REST", "note": "Istirahat total, hidrasi optimal, asupan karbohidrat seimbang, tidur cukup."})
day("2027-05-30", {"type": "RACE", "km": 21.1, "pace": 495,
                   "note": "BFI Run 2027 Half Marathon (21,1 km, COT 3 jam) di ICE BSD City. Mulai konservatif 5 km awal "
                           "(~8:15–8:30/km), evaluasi ritme setelah km 10 menuju finis < 3 jam."})

# warm-up variation on running sessions, rotating weekly
for k, sess in D.items():
    week = (date.fromisoformat(k) - date(2026, 11, 23)).days // 7
    for s in sess:
        if s["type"] in ("RW", "LRW", "LONG", "N4X4"):
            s["warmup"] = week % 3

start, end = date(2026, 11, 26), date(2027, 5, 30)
expected = {(start + timedelta(days=i)).isoformat() for i in range((end - start).days + 1)}
assert set(D) == expected, sorted(expected ^ set(D))  # every day from the PDF, none missing or extra

plan = {"name": "BFI Run 2027 Half Marathon", "event_date": "2027-05-30", "distance": "half", "goal_time": "3:00",
        "days": [{"date": k, "sessions": D[k]} for k in sorted(D)]}
out = Path(__file__).with_name("bfi-run-2027-half-marathon.json")
out.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"wrote {out} ({len(D)} days)")
