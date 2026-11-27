from datetime import date

from app.i18n import fmt_date, pick, plan_text, t
from app.plan import Stats, adapt, build_plan


def test_generated_sessions_and_adjustments_have_indonesian_text():
    from app.sessions import describe, label, warmup
    days = {d.date: d.__dict__ for d in build_plan(Stats(6, 4, 560), "half", date(2027, 5, 30), 4,
                                                   today=date(2026, 11, 23))}
    days |= {d.date: d.__dict__ for d in build_plan(Stats(30, 14, 360), "half", date(2027, 5, 30), 4,
                                                    goal_s=7200, today=date(2026, 11, 23))}
    for d in days.values():
        for x in d["sessions"]:
            if x["type"] not in ("N4X4",):
                assert label(x, "id") != label(x, "en") or x["type"] in ("STRIDES",), x
            assert describe(x, "id") != describe(x, "en"), x
            if x.get("warmup") is not None:
                assert warmup(x, "id").startswith("Pemanasan")
    adapt(days, {}, "2026-11-30", -30)
    labels = {d["adjusted"] for d in days.values() if d.get("adjusted")}
    labels |= {"Long run moved here from Sun (missed)", "Easy instead of hard: the day after a long run",
               "Easy, conversational effort"}
    # details stored by plans created before sessions existed
    labels |= {"Easy at 6:25/km", "Rest or light mobility", "Long run, conversational at 6:25/km",
               "Warm up 2 km, 6×800 m at 5:05/km with 400 m jog, cool down",
               "Warm up 2 km, 3 km at 5:35/km, cool down", "Race day! Target 5:41/km"}
    untranslated = [x for x in labels if plan_text(x, "id") == x]
    assert not untranslated, untranslated
    assert plan_text("Long run moved here from Sun (missed)", "id").endswith("dari Min (terlewat)")


def test_strings_dates_and_language_pick():
    assert t("Log out", "id") == "Keluar" and t("Log out", "en") == "Log out"
    assert t("not in dictionary", "id") == "not in dictionary"
    assert fmt_date("2026-11-30", "%a %d %b", "id") == "Sen 30 Nov"
    assert fmt_date("2027-05-30", "%d %b %Y", "id") == "30 Mei 2027"
    assert fmt_date("2027-05-30", "%d %b %Y", "en") == "30 May 2027"
    assert pick("id-ID,id;q=0.9,en;q=0.8") == "id" and pick("en-US") == "en" and pick("") == "en"
