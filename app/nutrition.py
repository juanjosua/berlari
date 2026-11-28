"""Daily nutrition targets and meal suggestions from everyday Indonesian food: the warteg / food-stall lunch
plus items from Indomaret, Alfamart and FamilyMart. Pure, no I/O.

Numbers are rounded estimates (kcal, protein g, carbs g) for typical portions; product values come from
package labels quoted in Indonesian food articles and nutrition databases, and vary by brand and size.
This is general guidance for healthy weight loss while training, not a medical diet."""

# name (en, id), kcal, protein, carbs, where to get it, price (Rp, rough Jakarta-area estimate, late 2026)
FOODS = {
    "egg": (("2 boiled eggs", "2 telur rebus"), 150, 12, 1, ("cook at home (raw eggs at Indomaret)", "rebus di rumah (telur mentah ada di Indomaret)"), 6000),
    "bread": (("2 slices whole-wheat bread (Sari Roti Gandum)", "2 lembar roti gandum (Sari Roti Gandum)"), 140, 5, 26, ("Indomaret / Alfamart", "Indomaret / Alfamart"), 3000),
    "banana": (("1 banana", "1 pisang"), 105, 1, 27, ("Indomaret / Alfamart fruit shelf", "rak buah Indomaret / Alfamart"), 4000),
    "oats": (("Oatmeal 40 g (Quaker) cooked with water", "Oatmeal 40 g (Quaker) dimasak dengan air"), 150, 5, 27, ("Indomaret / Alfamart", "Indomaret / Alfamart"), 2500),
    "milk": (("Low-fat milk 200 ml (Diamond / Greenfields)", "Susu rendah lemak 200 ml (Diamond / Greenfields)"), 95, 6, 10, ("Indomaret / Alfamart", "Indomaret / Alfamart"), 6500),
    "yogurt_drink": (("Cimory Yogurt Drink Low Fat 189 ml", "Cimory Yogurt Drink Low Fat 189 ml"), 120, 6, 18, ("Indomaret / Alfamart / FamilyMart", "Indomaret / Alfamart / FamilyMart"), 9000),
    "greek": (("Plain Greek yogurt 100 g (check label: low sugar)", "Greek yogurt plain 100 g (cek label: rendah gula)"), 90, 8, 6, ("Indomaret / Alfamart chiller", "chiller Indomaret / Alfamart"), 12000),
    "lmen_bar": (("L-Men Crunchy bar 22 g", "L-Men Crunchy bar 22 g"), 90, 7, 11, ("Indomaret / Alfamart", "Indomaret / Alfamart"), 7000),
    "fitbar": (("1 Fitbar", "1 Fitbar"), 100, 3, 16, ("Indomaret / Alfamart", "Indomaret / Alfamart"), 4500),
    "onigiri": (("1 tuna onigiri", "1 onigiri tuna"), 190, 6, 34, ("FamilyMart / Indomaret", "FamilyMart / Indomaret"), 12000),
    "rice": (("1 scoop rice (centong, ~100 g)", "1 centong nasi (~100 g)"), 130, 3, 28, ("", ""), 5000),
    "fish": (("Grilled or steamed fish (ikan bakar / pepes), not fried", "Ikan bakar / pepes, bukan goreng"), 160, 25, 0, ("warteg / food stall", "warteg / warung"), 13000),
    "chicken": (("Grilled chicken, skin removed (ayam bakar)", "Ayam bakar tanpa kulit"), 190, 30, 2, ("warteg / food stall", "warteg / warung"), 15000),
    "tempe": (("2 pieces tempe bacem or steamed", "2 potong tempe bacem / kukus"), 160, 12, 10, ("warteg / food stall", "warteg / warung"), 4000),
    "tahu": (("2 pieces steamed or bacem tofu", "2 potong tahu kukus / bacem"), 90, 9, 3, ("warteg / food stall", "warteg / warung"), 4000),
    "veg": (("Clear-soup or lightly stir-fried greens (kangkung / sawi / labu siam), a big portion",
             "Sayur bening atau tumis ringan (kangkung / sawi / labu siam), porsi besar"), 50, 3, 7, ("warteg / food stall", "warteg / warung"), 4000),
    "ubi": (("Boiled sweet potato (ubi rebus), ~200 g", "Ubi rebus, ~200 g"), 180, 3, 40, ("warung / cook at home", "warung / rebus di rumah"), 5000),
    "isotonic": (("Pocari Sweat or Hydro Coco during the run", "Pocari Sweat atau Hydro Coco saat lari"), 120, 0, 30, ("Indomaret / Alfamart", "Indomaret / Alfamart"), 8000),
}

# Two meals a day (the athlete's habit): lunch at a stall and an afternoon meal around 4-5 pm, plus a small
# pre-run snack only on long-run days (2+ hours on an empty stomach is risky). Rotated by day for variety.
LUNCH = [["fish", "tempe", "veg", "rice"], ["chicken", "tahu", "veg", "rice"], ["egg", "tempe", "veg", "rice"]]
AFTERNOON = [["banana", "egg", "milk"], ["bread", "egg", "banana"], ["yogurt_drink", "banana", "egg"]]
# Weekends at home when rice is a weekend thing: two family meals with rice.
HOME = [["rice", "chicken", "veg", "tempe"], ["rice", "fish", "veg", "tahu"]]
# extras that make sense in each meal, added in turn until the day's calorie target is met
# cheap, filling foods first (tempe, tahu, eggs, bananas, bread) so the day stays affordable
ADD_ONS = {"lunch": ["rice", "tempe", "egg", "tahu"], "afternoon": ["banana", "bread", "egg", "milk"],
           "home_1": ["rice", "tempe", "egg"], "home_2": ["rice", "tahu", "banana"],
           "after_run": ["bread", "banana", "fitbar", "milk"]}
MAX_SAME = 2  # portions of one food per meal (3 on long-run days), so menus stay realistic
ONE_PER_MEAL = {"egg", "fish", "chicken", "veg", "yogurt_drink", "greek"}  # "egg" is already 2 eggs
RICE_FOODS = {"rice", "onigiri"}
NO_RICE_SWAP = {"lunch": ["ubi", "tempe", "egg", "tahu"], "afternoon": ["bread", "banana", "oats", "egg"],
                "home_1": ["ubi", "tempe", "egg"], "home_2": ["ubi", "tahu", "banana"],
                "after_run": ["bread", "banana", "fitbar", "milk"]}

SLOTS = [("pre_run", ("Before the long run (30–60 min before)", "Sebelum lari jauh (30–60 menit sebelumnya)")),
         ("after_run", ("Right after the long run", "Segera setelah lari jauh")),
         ("home_1", ("Meal 1 at home (pick from what your family bought)", "Makan 1 di rumah (pilih dari yang dibeli keluarga)")),
         ("home_2", ("Meal 2 at home", "Makan 2 di rumah")),
         ("lunch", ("Lunch (your usual stall, upgraded)", "Makan siang (warung biasamu, versi lebih sehat)")),
         ("afternoon", ("Afternoon meal (around 4–5 pm)", "Makan sore (sekitar jam 4–5)"))]


def bmr(kg: float, cm: float, age: int, sex: str) -> float:
    """Mifflin-St Jeor resting energy (kcal/day)."""
    return 10 * kg + 6.25 * cm - 5 * age + (5 if sex == "M" else -161)


def exercise_kcal(sessions: list[dict], kg: float, easy_pace_s: float) -> float:
    """Rough energy cost of the day's planned sessions: ~1 kcal per kg per km running, less for run-walk."""
    total = 0.0
    for s in sessions:
        km = s.get("km") or ((s.get("minutes") or 0) * 60 / easy_pace_s if s.get("minutes") else 0)
        if s["type"] in ("EASY", "LONG", "TEMPO", "INT", "RACE"):
            factor = 0.85 if s.get("var") in ("runwalk", "walk_breaks") else 1.0
            total += kg * km * factor
        elif s["type"] == "SBW":
            total += 4 * kg * 0.4  # ~25 min of bodyweight strength at ~4 MET
    return total


def targets(kg: float, cm: float, age: int, sex: str, sessions: list[dict], easy_pace_s: float,
            days_to_race: int) -> dict:
    """Calories, protein and carbs for one day.
    - Energy: resting x 1.3 (daily life) + planned training - a deficit for gradual weight loss.
    - Deficit ~500 kcal on easy/rest days (about 0.5 kg a week), smaller on long or hard days so training is
      fuelled, none in race week. Never below resting energy.
    - Protein 1.5 g per kg of a healthy reference weight (BMI 25) to keep muscle while losing fat.
    - Carbs scale with how hard the day is; extra the day before the race."""
    bmi = kg / (cm / 100) ** 2
    ref_kg = min(kg, 25 * (cm / 100) ** 2)
    rest = bmr(kg, cm, age, sex)
    burn = rest * 1.3 + exercise_kcal(sessions, kg, easy_pace_s)
    types = {s["type"] for s in sessions}
    heavy = bool(types & {"LONG", "INT", "TEMPO", "RACE"})
    # BMI 30+: a bigger (still standard 500-1000 kcal) gap; the floor below keeps it at or above resting needs
    deficit = 0 if days_to_race <= 7 or bmi < 25 else (400 if heavy else 750) if bmi >= 30 else (300 if heavy else 500)
    kcal = max(burn - deficit, rest, 1500 if sex == "M" else 1200)
    carb_per_kg = (6 if days_to_race == 1 else 4.5 if "LONG" in types or "RACE" in types else
                   3.5 if heavy else 3 if types & {"EASY", "SBW"} else 2.5)
    gap = max(0, burn - kcal)  # the real deficit after the resting-energy floor
    return {"kcal": round(kcal / 10) * 10, "protein": round(1.5 * ref_kg), "carbs": round(carb_per_kg * ref_kg),
            "burn": round(burn / 10) * 10, "deficit": round(gap), "loss_per_week_kg": round(gap * 7 / 7700, 2)}


def day_meals(day_index: int, sessions: list[dict], target: dict, rice: str = "daily", weekend: bool = False) -> dict:
    """Two meals for one day, rotated for variety and topped up with extras to reach the calorie target.
    rice: "daily", "weekend" (rice only on Sat/Sun, eaten at home) or "none"."""
    rice_today = rice == "daily" or (rice == "weekend" and weekend)
    if rice == "weekend" and weekend:
        meals = {"home_1": list(HOME[day_index % 2]), "home_2": list(HOME[(day_index + 1) % 2])}
    else:
        meals = {"lunch": list(LUNCH[day_index % 3]), "afternoon": list(AFTERNOON[(day_index + 1) % 3])}
    if not rice_today:
        meals = {k: [f for f in v if f not in RICE_FOODS] for k, v in meals.items()}
    types = {s["type"] for s in sessions}
    if "LONG" in types or "RACE" in types:
        meals["pre_run"] = ["banana"]
        meals["during"] = ["isotonic"] if any((s.get("km") or 0) >= 12 for s in sessions) else []
        meals["after_run"] = ["yogurt_drink", "banana"]  # carbs + protein within an hour of finishing
    cap = MAX_SAME + (1 if types & {"LONG", "RACE", "INT", "TEMPO"} else 0)
    slots = [k for k in meals if k in ADD_ONS]
    total = sum(FOODS[f][1] for m in meals.values() for f in m)
    i = 0
    while total < target["kcal"] - 80 and i < 40:  # top up toward the target, alternating the two meals
        slot = slots[i % len(slots)]
        extras = ADD_ONS[slot] if rice_today else NO_RICE_SWAP.get(slot, ADD_ONS[slot])
        start = (i // len(slots)) % len(extras)
        food = next((extras[(start + k) % len(extras)] for k in range(len(extras))
                     if meals[slot].count(extras[(start + k) % len(extras)]) <
                     (1 if extras[(start + k) % len(extras)] in ONE_PER_MEAL else cap)), None)
        i += 1
        if food is None:
            continue  # this meal is full; the other one gets the next extra
        meals[slot].append(food)
        total += FOODS[food][1]
    protein = sum(FOODS[f][2] for m in meals.values() for f in m)
    price = sum(FOODS[f][5] for m in meals.values() for f in m)
    return {"meals": meals, "kcal": total, "protein": protein, "price": price}


TIPS = [
    ("Choose bakar, pepes, kukus or rebus instead of goreng: the same fish or chicken fried can carry 100–200 kcal of extra oil.",
     "Pilih bakar, pepes, kukus atau rebus, bukan goreng: ikan atau ayam yang sama kalau digoreng bisa membawa 100–200 kkal minyak tambahan."),
    ("Fill half the plate with vegetables first; they keep you full for very few calories.",
     "Isi setengah piring dengan sayur dulu; bikin kenyang dengan kalori sangat sedikit."),
    ("Drink water through the day (about 2.5–3 litres in Jakarta heat), more on run days. Skip sweet tea and sugary drinks.",
     "Minum air sepanjang hari (sekitar 2,5–3 liter di cuaca panas), lebih banyak di hari lari. Hindari es teh manis dan minuman bergula."),
    ("Eat protein at every meal (egg, fish, chicken, tempe, tahu, yogurt): it protects muscle while you lose fat.",
     "Makan protein di setiap waktu makan (telur, ikan, ayam, tempe, tahu, yogurt): menjaga otot selagi lemak turun."),
    ("With only two meals, make both count: protein and vegetables first, rice last. Eating far below your target makes "
     "training feel heavy and often ends in overeating.",
     "Dengan dua kali makan, buat keduanya bernilai: protein dan sayur dulu, nasi terakhir. Makan jauh di bawah target "
     "membuat latihan terasa berat dan sering berakhir makan berlebihan."),
]


def grouped(items: list[str]) -> list[tuple[str, int]]:
    """['rice', 'egg', 'rice'] -> [('rice', 2), ('egg', 1)], keeping first-seen order (for display)."""
    out: dict[str, int] = {}
    for f in items:
        out[f] = out.get(f, 0) + 1
    return list(out.items())
