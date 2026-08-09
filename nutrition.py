"""
Расчёт суточной нормы калорий и БЖУ по антропометрии.
Формула Миффлина-Сан Жеора — общепринятый способ прикинуть базовый обмен (BMR),
дальше умножаем на коэффициент активности (TDEE) и подстраиваем под цель.
"""

ACTIVITY_LEVELS = {
    "sedentary":    ("🪑 Минимальная — сидячая работа, без тренировок", 1.2),
    "light":        ("🚶 Лёгкая — 1-3 тренировки в неделю", 1.375),
    "moderate":     ("🏃 Средняя — 3-5 тренировок в неделю", 1.55),
    "active":       ("🏋️ Высокая — 6-7 тренировок в неделю", 1.725),
    "very_active":  ("🔥 Очень высокая — физическая работа + спорт", 1.9),
}

GOAL_ADJUST = {"loss": -0.15, "gain": 0.15, "maintain": 0.0, "variety": 0.0}


def bmr(sex: str, age: float, height_cm: float, weight_kg: float) -> float:
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if sex == "m" else base - 161


def tdee(bmr_value: float, activity_key: str) -> float:
    factor = ACTIVITY_LEVELS.get(activity_key, ACTIVITY_LEVELS["sedentary"])[1]
    return bmr_value * factor


def target_calories(tdee_value: float, goal: str) -> float:
    return tdee_value * (1 + GOAL_ADJUST.get(goal, 0.0))


def macros_target(calories: float, weight_kg: float, goal: str) -> dict:
    protein_per_kg = 1.8 if goal in ("loss", "gain") else 1.4
    protein_g = weight_kg * protein_per_kg
    fat_g = calories * 0.27 / 9
    carbs_kcal = max(calories - protein_g * 4 - fat_g * 9, 0)
    return {
        "kcal": round(calories),
        "protein": round(protein_g),
        "fat": round(fat_g),
        "carbs": round(carbs_kcal / 4),
    }


def full_profile_targets(profile: dict, goal: str) -> dict:
    """profile: {sex, age, height, weight, activity}. Возвращает bmr/tdee/дневную норму с БЖУ."""
    b = bmr(profile["sex"], profile["age"], profile["height"], profile["weight"])
    t = tdee(b, profile["activity"])
    target = target_calories(t, goal)
    macros = macros_target(target, profile["weight"], goal)
    return {"bmr": round(b), "tdee": round(t), **macros}


def profile_complete(profile: dict) -> bool:
    return all(profile.get(k) is not None for k in ("sex", "age", "height", "weight", "activity"))
