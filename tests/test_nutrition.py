from app.nutrition import FOODS, bmr, day_meals, grouped, targets

EASY = 572  # s/km


def test_targets_give_gentle_deficit_and_fuel_hard_days():
    assert round(bmr(102, 170, 30, "M")) == 1938  # Mifflin-St Jeor
    rest = targets(102, 170, 30, "M", [{"type": "REST"}], EASY, 100)
    long = targets(102, 170, 30, "M", [{"type": "LONG", "km": 15}], EASY, 100)
    race_week = targets(102, 170, 30, "M", [{"type": "EASY", "km": 3}], EASY, 5)
    assert rest["deficit"] == 500 and 0.4 <= rest["loss_per_week_kg"] <= 0.5  # ~0.5 kg/week, not a crash diet
    assert long["kcal"] > rest["kcal"] + 1000 and long["deficit"] == 300 and long["carbs"] > rest["carbs"]
    assert race_week["deficit"] == 0
    assert rest["kcal"] >= bmr(102, 170, 30, "M")  # never below resting needs
    assert rest["protein"] == round(1.5 * 25 * 1.7 ** 2)  # protein from a healthy reference weight
    lean = targets(65, 175, 30, "M", [{"type": "REST"}], EASY, 100)
    assert lean["deficit"] == 0  # BMI under 25: eat to fuel training, no deficit


def test_meals_reach_target_and_use_real_foods():
    for sess in ([{"type": "REST"}], [{"type": "SBW"}], [{"type": "LONG", "km": 15}]):
        t = targets(102, 170, 30, "M", sess, EASY, 100)
        m = day_meals(7, sess, t)
        assert abs(m["kcal"] - t["kcal"]) <= 150 and m["protein"] >= t["protein"] * 0.9
        assert all(f in FOODS for items in m["meals"].values() for f in items)
    long = day_meals(7, [{"type": "LONG", "km": 15}], targets(102, 170, 30, "M", [{"type": "LONG", "km": 15}], EASY, 100))
    assert long["meals"]["during"] == ["isotonic"] and "yogurt_drink" in long["meals"]["snack"]
    assert day_meals(1, [], {"kcal": 1500})["meals"] != day_meals(2, [], {"kcal": 1500})["meals"]  # varies by day
    assert grouped(["rice", "egg", "rice"]) == [("rice", 2), ("egg", 1)]
