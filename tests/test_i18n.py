from datetime import date

from app.i18n import fmt_date, pick, plan_text, t
from app.plan import Stats, adapt, build_plan


def test_every_generated_plan_text_has_an_indonesian_version():
    texts = set()
    for dist in ("5k", "10k", "half", "marathon"):
        for goal in (None, 3600):
            for d in build_plan(Stats(20, 10, 390), dist, date(2027, 3, 7), 4, goal, today=date(2026, 11, 25)):
                texts.add(d.detail)
    # adaptation labels and details
    days = {d.date: d.__dict__ for d in build_plan(Stats(20, 10, 390), "half", date(2027, 3, 7), 4,
                                                   today=date(2026, 11, 23))}
    adapt(days, {}, "2026-11-30", -30)  # Monday after a fully missed week, very tired
    texts |= {d["detail"] for d in days.values()} | {d["adjusted"] for d in days.values() if d.get("adjusted")}
    texts |= {"Long run moved here from Sun (missed)", "Easy instead of hard: the day after a long run"}
    untranslated = [x for x in texts if plan_text(x, "id") == x]
    assert not untranslated, untranslated
    assert plan_text("Easy at 6:25/km", "id") == "Lari santai di 6:25/km"
    assert plan_text("Long run moved here from Sun (missed)", "id").endswith("dari Min (terlewat)")
    assert plan_text("Easy at 6:25/km", "en") == "Easy at 6:25/km"


def test_strings_dates_and_language_pick():
    assert t("Log out", "id") == "Keluar" and t("Log out", "en") == "Log out"
    assert t("not in dictionary", "id") == "not in dictionary"
    assert fmt_date("2026-11-30", "%a %d %b", "id") == "Sen 30 Nov"
    assert fmt_date("2027-05-30", "%d %b %Y", "id") == "30 Mei 2027"
    assert fmt_date("2027-05-30", "%d %b %Y", "en") == "30 May 2027"
    assert pick("id-ID,id;q=0.9,en;q=0.8") == "id" and pick("en-US") == "en" and pick("") == "en"
