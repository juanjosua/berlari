from app.nutrition import FOODS, bmr, day_meals, grouped, targets

EASY = 572  # s/km


def test_targets_give_gentle_deficit_and_fuel_hard_days():
    assert round(bmr(102, 170, 30, "M")) == 1938  # Mifflin-St Jeor
    rest = targets(102, 170, 30, "M", [{"type": "REST"}], EASY, 100)
    long = targets(102, 170, 30, "M", [{"type": "LONG", "km": 15}], EASY, 100)
    race_week = targets(102, 170, 30, "M", [{"type": "EASY", "km": 3}], EASY, 5)
    assert 500 <= rest["deficit"] <= 750 and 0.45 <= rest["loss_per_week_kg"] <= 0.7  # steady, not a crash diet
    assert rest["burn"] > rest["kcal"]  # eating less than the body uses, so weight goes down
    assert long["kcal"] > rest["kcal"] + 1000 and long["deficit"] == 400 and long["carbs"] > rest["carbs"]
    assert race_week["deficit"] == 0
    mid = targets(85, 170, 30, "M", [{"type": "REST"}], EASY, 100)  # BMI 29.4: standard 500 gap
    assert mid["deficit"] == 500
    assert rest["kcal"] >= 1500  # BMI 30+: never below the usual weight-loss intake for men (NIH 1,500-1,800)
    assert targets(80, 180, 30, "M", [{"type": "REST"}], EASY, 100)["kcal"] >= bmr(80, 180, 30, "M")  # BMI < 30: resting floor
    assert rest["protein"] == round(1.5 * 25 * 1.7 ** 2)  # protein from a healthy reference weight
    lean = targets(65, 175, 30, "M", [{"type": "REST"}], EASY, 100)
    assert lean["deficit"] == 0  # BMI under 25: eat to fuel training, no deficit


def test_meals_reach_target_and_use_real_foods():
    for sess in ([{"type": "REST"}], [{"type": "SBW"}], [{"type": "LONG", "km": 15}]):  # lunch + afternoon only
        t = targets(102, 170, 30, "M", sess, EASY, 100)
        m = day_meals(7, sess, t)
        assert abs(m["kcal"] - t["kcal"]) <= 150 and m["protein"] >= t["protein"] * 0.9
        assert all(f in FOODS for items in m["meals"].values() for f in items)
    long = day_meals(7, [{"type": "LONG", "km": 15}], targets(102, 170, 30, "M", [{"type": "LONG", "km": 15}], EASY, 100))
    assert long["meals"]["during"] == ["isotonic"] and long["meals"]["pre_run"] == ["banana"]
    assert long["meals"]["after_run"][:2] == ["yogurt_drink", "banana"]
    rest = day_meals(7, [{"type": "REST"}], targets(102, 170, 30, "M", [{"type": "REST"}], EASY, 100))
    assert set(rest["meals"]) == {"lunch", "afternoon"}  # no breakfast or dinner
    assert day_meals(1, [], {"kcal": 1500})["meals"] != day_meals(2, [], {"kcal": 1500})["meals"]  # varies by day
    assert grouped(["rice", "egg", "rice"]) == [("rice", 2), ("egg", 1)]


def test_rice_preference_weekend_home_meals_and_price():
    t = targets(102, 170, 30, "M", [{"type": "SBW"}], EASY, 100)
    weekday = day_meals(5, [{"type": "SBW"}], t, rice="weekend", weekend=False)
    weekend = day_meals(5, [{"type": "SBW"}], t, rice="weekend", weekend=True)
    flat = lambda m: [f for v in m["meals"].values() for f in v]  # noqa: E731
    assert "rice" not in flat(weekday) and "onigiri" not in flat(weekday)
    assert set(weekend["meals"]) == {"home_1", "home_2"} and flat(weekend).count("rice") >= 2
    assert all(m.count("rice") <= 2 and m.count("egg") <= 1 for m in weekend["meals"].values())
    assert weekday["price"] == sum(FOODS[f][5] for f in flat(weekday)) and 30000 < weekday["price"] < 100000
    assert all("home" not in FOODS[f][4][0] for f in FOODS)  # nothing to cook: warteg or minimarket only
    assert "rice" in flat(day_meals(5, [{"type": "SBW"}], t))  # default: rice every day


def test_weekday_budget_caps_price_and_flags_shortfall():
    t = targets(102, 170, 30, "M", [{"type": "EASY", "km": 3}], EASY, 100)
    tight = day_meals(5, [{"type": "EASY", "km": 3}], t, rice="weekend", weekend=False, budget=40000)
    assert tight["price"] <= 40000 and tight["budget_limited"] and tight["kcal"] < t["kcal"]
    roomy = day_meals(5, [{"type": "EASY", "km": 3}], t, rice="weekend", weekend=False, budget=200000)
    assert not roomy["budget_limited"] and abs(roomy["kcal"] - t["kcal"]) <= 150
    home = day_meals(5, [{"type": "REST"}], targets(102, 170, 30, "M", [{"type": "REST"}], EASY, 100),
                     rice="weekend", weekend=True, budget=40000)
    assert not home["budget_limited"]  # weekend family meals aren't limited by the weekday budget
