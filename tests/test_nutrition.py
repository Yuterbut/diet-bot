"""Тесты чистой математики из nutrition.py — формула Миффлина-Сан Жеора,
коэффициенты активности, цель по калориям и раскладка БЖУ."""

import pytest

import nutrition


# ---------- BMR ----------

def test_bmr_male_matches_mifflin_st_jeor():
    # 10*80 + 6.25*180 - 5*30 + 5 = 1780
    assert nutrition.bmr("m", age=30, height_cm=180, weight_kg=80) == pytest.approx(1780.0)


def test_bmr_female_matches_mifflin_st_jeor():
    # 10*60 + 6.25*165 - 5*30 - 161 = 1320.25
    assert nutrition.bmr("f", age=30, height_cm=165, weight_kg=60) == pytest.approx(1320.25)


def test_bmr_male_is_higher_than_female_for_same_body():
    male = nutrition.bmr("m", 30, 175, 70)
    female = nutrition.bmr("f", 30, 175, 70)
    assert male - female == pytest.approx(166.0)


def test_bmr_treats_any_non_male_sex_as_female():
    assert nutrition.bmr("x", 30, 165, 60) == nutrition.bmr("f", 30, 165, 60)


# ---------- TDEE ----------

@pytest.mark.parametrize("activity,factor", [
    ("sedentary", 1.2),
    ("light", 1.375),
    ("moderate", 1.55),
    ("active", 1.725),
    ("very_active", 1.9),
])
def test_tdee_applies_activity_multiplier(activity, factor):
    assert nutrition.tdee(1780.0, activity) == pytest.approx(1780.0 * factor)


def test_tdee_unknown_activity_falls_back_to_sedentary():
    assert nutrition.tdee(1780.0, "no_such_level") == pytest.approx(1780.0 * 1.2)


def test_tdee_none_activity_falls_back_to_sedentary():
    assert nutrition.tdee(1780.0, None) == pytest.approx(1780.0 * 1.2)


# ---------- Целевые калории ----------

@pytest.mark.parametrize("goal,expected", [
    ("loss", 1700.0),
    ("gain", 2300.0),
    ("maintain", 2000.0),
    ("variety", 2000.0),
])
def test_target_calories_per_goal(goal, expected):
    assert nutrition.target_calories(2000.0, goal) == pytest.approx(expected)


def test_target_calories_unknown_goal_keeps_tdee():
    assert nutrition.target_calories(2000.0, "unknown") == pytest.approx(2000.0)


# ---------- БЖУ ----------

def test_macros_target_loss_exact_split():
    # белок 80*1.8=144 г, жир 2000*0.27/9=60 г, углеводы (2000-576-540)/4=221 г
    assert nutrition.macros_target(2000, 80, "loss") == {
        "kcal": 2000, "protein": 144, "fat": 60, "carbs": 221,
    }


def test_macros_target_maintain_uses_lower_protein_than_loss():
    loss = nutrition.macros_target(2000, 80, "loss")
    maintain = nutrition.macros_target(2000, 80, "maintain")
    assert loss["protein"] == 144
    assert maintain["protein"] == 112
    assert maintain["carbs"] > loss["carbs"]


def test_macros_target_gain_uses_same_high_protein_as_loss():
    assert (nutrition.macros_target(2000, 80, "gain")["protein"]
            == nutrition.macros_target(2000, 80, "loss")["protein"])


def test_macros_target_protein_scales_with_weight():
    light = nutrition.macros_target(2000, 60, "loss")["protein"]
    heavy = nutrition.macros_target(2000, 100, "loss")["protein"]
    assert light == 108
    assert heavy == 180


def test_macros_target_fat_is_27_percent_of_calories():
    assert nutrition.macros_target(3000, 80, "maintain")["fat"] == round(3000 * 0.27 / 9)


def test_macros_target_carbs_clamped_at_zero_when_protein_and_fat_exceed_calories():
    # 100 кг * 1.8 = 180 г белка (720 ккал) + жир 800*0.27 = 216 ккал -> уже 936 > 800
    macros = nutrition.macros_target(800, 100, "loss")
    assert macros["carbs"] == 0
    assert macros["protein"] * 4 + macros["fat"] * 9 > macros["kcal"]


def test_macros_target_carbs_never_negative_for_extreme_input():
    assert nutrition.macros_target(100, 200, "gain")["carbs"] == 0


# ---------- Композиция ----------

def test_full_profile_targets_composes_bmr_tdee_and_macros():
    profile = {"sex": "m", "age": 30, "height": 180, "weight": 80, "activity": "moderate"}
    result = nutrition.full_profile_targets(profile, "loss")

    assert result["bmr"] == 1780
    assert result["tdee"] == round(1780 * 1.55)
    assert result["kcal"] == round(1780 * 1.55 * 0.85)
    assert result["protein"] == 144
    assert set(result) == {"bmr", "tdee", "kcal", "protein", "fat", "carbs"}


# ---------- Полнота анкеты ----------

def test_profile_complete_true_for_all_fields_filled():
    assert nutrition.profile_complete(
        {"sex": "f", "age": 28, "height": 165, "weight": 60, "activity": "light"}) is True


def test_profile_complete_ignores_extra_fields():
    assert nutrition.profile_complete(
        {"sex": "f", "age": 28, "height": 165, "weight": 60,
         "activity": "light", "goal": "loss"}) is True


def test_profile_complete_false_when_field_missing():
    assert nutrition.profile_complete(
        {"sex": "f", "age": 28, "height": 165, "weight": 60}) is False


def test_profile_complete_false_when_field_is_explicitly_none():
    # частый случай: поле создано в анкете, но пользователь его ещё не заполнил
    assert nutrition.profile_complete(
        {"sex": "f", "age": 28, "height": None, "weight": 60, "activity": "light"}) is False


def test_profile_complete_false_for_empty_profile():
    assert nutrition.profile_complete({}) is False
