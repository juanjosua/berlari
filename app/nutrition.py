"""Daily nutrition targets and meal suggestions from everyday Indonesian food: the warteg / food-stall lunch
plus items from Indomaret, Alfamart and FamilyMart. Pure, no I/O.

Numbers are rounded estimates (kcal, protein g, carbs g) for typical portions; product values come from
package labels quoted in Indonesian food articles and nutrition databases, and vary by brand and size.
This is general guidance for healthy weight loss while training, not a medical diet."""

# name (en, id), kcal, protein, carbs, where to get it
FOODS = {
    "egg": (("2 boiled eggs", "2 telur rebus"), 150, 12, 1, ("cook at home (raw eggs at Indomaret)", "rebus di rumah (telur mentah ada di Indomaret)")),
    "bread": (("2 slices whole-wheat bread (Sari Roti Gandum)", "2 lembar roti gandum (Sari Roti Gandum)"), 140, 5, 26, ("Indomaret / Alfamart", "Indomaret / Alfamart")),
    "banana": (("1 banana", "1 pisang"), 105, 1, 27, ("Indomaret / Alfamart fruit shelf", "rak buah Indomaret / Alfamart")),
    "oats": (("Oatmeal 40 g (Quaker) cooked with water", "Oatmeal 40 g (Quaker) dimasak dengan air"), 150, 5, 27, ("Indomaret / Alfamart", "Indomaret / Alfamart")),
    "milk": (("Low-fat milk 200 ml (Diamond / Greenfields)", "Susu rendah lemak 200 ml (Diamond / Greenfields)"), 95, 6, 10, ("Indomaret / Alfamart", "Indomaret / Alfamart")),
    "yogurt_drink": (("Cimory Yogurt Drink Low Fat 189 ml", "Cimory Yogurt Drink Low Fat 189 ml"), 120, 6, 18, ("Indomaret / Alfamart / FamilyMart", "Indomaret / Alfamart / FamilyMart")),
    "greek": (("Plain Greek yogurt 100 g (check label: low sugar)", "Greek yogurt plain 100 g (cek label: rendah gula)"), 90, 8, 6, ("Indomaret / Alfamart chiller", "chiller Indomaret / Alfamart")),
    "lmen_bar": (("L-Men Crunchy bar 22 g", "L-Men Crunchy bar 22 g"), 90, 7, 11, ("Indomaret / Alfamart", "Indomaret / Alfamart")),
    "fitbar": (("1 Fitbar", "1 Fitbar"), 100, 3, 16, ("Indomaret / Alfamart", "Indomaret / Alfamart")),
    "onigiri": (("1 tuna onigiri", "1 onigiri tuna"), 190, 6, 34, ("FamilyMart / Indomaret", "FamilyMart / Indomaret")),
    "rice": (("1 scoop rice (centong, ~100 g)", "1 centong nasi (~100 g)"), 130, 3, 28, ("", "")),
    "fish": (("Grilled or steamed fish (ikan bakar / pepes), not fried", "Ikan bakar / pepes, bukan goreng"), 160, 25, 0, ("warteg / food stall", "warteg / warung")),
    "chicken": (("Grilled chicken, skin removed (ayam bakar)", "Ayam bakar tanpa kulit"), 190, 30, 2, ("warteg / food stall", "warteg / warung")),
    "tempe": (("2 pieces tempe bacem or steamed", "2 potong tempe bacem / kukus"), 160, 12, 10, ("warteg / food stall", "warteg / warung")),
    "tahu": (("2 pieces steamed or bacem tofu", "2 potong tahu kukus / bacem"), 90, 9, 3, ("warteg / food stall", "warteg / warung")),
    "veg": (("Clear-soup or lightly stir-fried greens (kangkung / sawi / labu siam), a big portion",
             "Sayur bening atau tumis ringan (kangkung / sawi / labu siam), porsi besar"), 50, 3, 7, ("warteg / food stall", "warteg / warung")),
    "isotonic": (("Pocari Sweat or Hydro Coco during the run", "Pocari Sweat atau Hydro Coco saat lari"), 120, 0, 30, ("Indomaret / Alfamart", "Indomaret / Alfamart")),
}

# Meal options per slot; picked by rotating the day so meals vary.
BREAKFAST = [["egg", "bread"], ["oats", "milk", "banana"], ["greek", "banana", "bread"]]
LUNCH = [["fish", "tempe", "veg", "rice"], ["chicken", "tahu", "veg", "rice"], ["egg", "tempe", "veg", "rice"]]
SNACK = [["yogurt_drink", "banana"], ["lmen_bar", "milk"], ["fitbar", "egg"]]
DINNER = [["chicken", "veg"], ["fish", "tahu", "veg"], ["tempe", "tahu", "veg", "egg"]]
# extras that make sense in each meal, added in turn until the day's calorie target is met
ADD_ONS = {"lunch": ["rice", "tempe", "egg"], "dinner": ["rice", "tahu", "fish"], "breakfast": ["banana", "milk", "bread"],
           "snack": ["banana", "milk", "lmen_bar"]}

SLOTS = [("breakfast", ("Breakfast", "Sarapan")), ("lunch", ("Lunch (your usual stall, upgraded)", "Makan siang (warung biasamu, versi lebih sehat)")),
         ("snack", ("Afternoon / around your run", "Sore / sekitar waktu lari")), ("dinner", ("Light dinner", "Makan malam ringan"))]


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
    deficit = 0 if days_to_race <= 7 or bmi < 25 else (300 if heavy else 500)
    kcal = max(burn - deficit, rest, 1500 if sex == "M" else 1200)
    carb_per_kg = (6 if days_to_race == 1 else 4.5 if "LONG" in types or "RACE" in types else
                   3.5 if heavy else 3 if types & {"EASY", "SBW"} else 2.5)
    return {"kcal": round(kcal / 10) * 10, "protein": round(1.5 * ref_kg), "carbs": round(carb_per_kg * ref_kg),
            "deficit": deficit, "loss_per_week_kg": round(deficit * 7 / 7700, 2)}


def day_meals(day_index: int, sessions: list[dict], target: dict) -> dict:
    """Meal slots for one day, rotated for variety, topped up with add-ons to reach the calorie target."""
    pick = {"breakfast": BREAKFAST[day_index % 3], "lunch": LUNCH[(day_index + 1) % 3],
            "snack": SNACK[(day_index + 2) % 3], "dinner": DINNER[day_index % 3]}
    meals = {k: list(v) for k, v in pick.items()}
    types = {s["type"] for s in sessions}
    if "LONG" in types or "RACE" in types:
        meals["snack"] = ["yogurt_drink", "banana"]  # recovery: carbs + protein right after
        meals["during"] = ["isotonic"] if any((s.get("km") or 0) >= 12 for s in sessions) else []
    total = sum(FOODS[f][1] for m in meals.values() for f in m)
    i = 0
    while total < target["kcal"] - 80 and i < 24:  # top up toward the target, one meal at a time
        slot = ["lunch", "dinner", "breakfast", "snack"][i % 4]
        food = ADD_ONS[slot][(i // 4) % len(ADD_ONS[slot])]
        meals[slot].append(food)
        total += FOODS[food][1]
        i += 1
    protein = sum(FOODS[f][2] for m in meals.values() for f in m)
    return {"meals": meals, "kcal": total, "protein": protein}


TIPS = [
    ("Choose bakar, pepes, kukus or rebus instead of goreng: the same fish or chicken fried can carry 100–200 kcal of extra oil.",
     "Pilih bakar, pepes, kukus atau rebus, bukan goreng: ikan atau ayam yang sama kalau digoreng bisa membawa 100–200 kkal minyak tambahan."),
    ("Fill half the plate with vegetables first; they keep you full for very few calories.",
     "Isi setengah piring dengan sayur dulu; bikin kenyang dengan kalori sangat sedikit."),
    ("Drink water through the day (about 2.5–3 litres in Jakarta heat), more on run days. Skip sweet tea and sugary drinks.",
     "Minum air sepanjang hari (sekitar 2,5–3 liter di cuaca panas), lebih banyak di hari lari. Hindari es teh manis dan minuman bergula."),
    ("Eat protein at every meal (egg, fish, chicken, tempe, tahu, yogurt): it protects muscle while you lose fat.",
     "Makan protein di setiap waktu makan (telur, ikan, ayam, tempe, tahu, yogurt): menjaga otot selagi lemak turun."),
    ("Don't skip breakfast on training days: running on an empty stomach for long sessions makes you overeat later.",
     "Jangan lewatkan sarapan di hari latihan: lari lama dengan perut kosong membuatmu makan berlebihan setelahnya."),
]


def grouped(items: list[str]) -> list[tuple[str, int]]:
    """['rice', 'egg', 'rice'] -> [('rice', 2), ('egg', 1)], keeping first-seen order (for display)."""
    out: dict[str, int] = {}
    for f in items:
        out[f] = out.get(f, 0) + 1
    return list(out.items())
