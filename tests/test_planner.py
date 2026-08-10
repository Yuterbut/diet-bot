"""Тесты planner.py: список покупок, генерация недельного плана,
правила разнообразия и суммарное КБЖУ дня.

Плана генерируется ровно столько, сколько нужно (фикстуры уровня модуля):
generate_plan делает до 40 попыток подбора, каждая — реальная работа.
random сеется явно, иначе результат менялся бы от запуска к запуску.
"""

import inspect
import math
import random
from unittest import mock

import pytest

import planner
from meals_data import MEALS
from products import PRODUCTS, pack_price

REGION = "center"
SEED = 20260810


def _meal(ingredients: dict) -> dict:
    """Минимальное «блюдо» — build_shopping_list смотрит только ingredients."""
    return {"name": "тест", "ingredients": ingredients}


def _make_plan(meals_per_day: int, goal: str = "variety", restrictions=frozenset(),
               budget=None, seed: int = SEED, **extra) -> dict:
    random.seed(seed)
    # get_price_overrides читает data.json с диска — подменяем, чтобы тесты
    # не зависели от локальных правок цен пользователя
    with mock.patch.object(planner, "get_price_overrides", return_value={}):
        return planner.generate_plan(goal, set(restrictions), meals_per_day, budget,
                                     REGION, **extra)


def _names(plan: list) -> list:
    return [[meal["name"] for meal in day] for day in plan]


@pytest.fixture(scope="module")
def plan3():
    return _make_plan(3)


@pytest.fixture(scope="module")
def plan5():
    return _make_plan(5)


# ---------- build_shopping_list ----------

def test_shopping_list_rounds_up_to_whole_packages():
    pack = PRODUCTS["oats"]["pack"]
    items, _, _ = planner.build_shopping_list([[_meal({"oats": pack + 1})]], REGION, overrides={})

    assert items[0]["packs"] == 2


def test_shopping_list_does_not_round_up_an_exact_package():
    pack = PRODUCTS["oats"]["pack"]
    items, _, _ = planner.build_shopping_list([[_meal({"oats": pack})]], REGION, overrides={})

    assert items[0]["packs"] == 1


def test_shopping_list_packs_equal_ceil_of_need():
    plan = [[_meal({"oats": 60, "banana": 100})], [_meal({"oats": 60})]]
    items, _, _ = planner.build_shopping_list(plan, REGION, overrides={})
    by_key = {i["key"]: i for i in items}

    assert by_key["oats"]["packs"] == math.ceil(120 / PRODUCTS["oats"]["pack"])
    assert by_key["banana"]["packs"] == math.ceil(100 / PRODUCTS["banana"]["pack"])


def test_shopping_list_cost_is_packs_times_price():
    pack = PRODUCTS["oats"]["pack"]
    items, total, _ = planner.build_shopping_list([[_meal({"oats": pack + 1})]], REGION, overrides={})

    assert items[0]["cost"] == round(2 * pack_price("oats", REGION))
    assert total == items[0]["cost"]


def test_shopping_list_bought_costs_more_than_eaten_when_package_is_partly_used():
    pack = PRODUCTS["oats"]["pack"]
    _, total, consumed = planner.build_shopping_list([[_meal({"oats": pack + 1})]], REGION, overrides={})

    assert total > consumed


def test_shopping_list_bought_never_cheaper_than_eaten():
    plan = [[_meal({"oats": 60, "banana": 100, "honey": 10, "milk_cow": 150})]]
    _, total, consumed = planner.build_shopping_list(plan, REGION, overrides={})

    assert total >= consumed


def test_shopping_list_sums_the_same_ingredient_across_days_and_meals():
    plan = [
        [_meal({"oats": 60}), _meal({"oats": 40})],
        [_meal({"oats": 50})],
    ]
    items, _, _ = planner.build_shopping_list(plan, REGION, overrides={})

    assert len(items) == 1
    assert items[0]["packs"] == math.ceil(150 / PRODUCTS["oats"]["pack"])


def test_shopping_list_is_sorted_by_cost_descending():
    plan = [[_meal({"oats": 60, "banana": 100, "honey": 10, "milk_cow": 150})]]
    items, _, _ = planner.build_shopping_list(plan, REGION, overrides={})

    costs = [i["cost"] for i in items]
    assert costs == sorted(costs, reverse=True)


def test_shopping_list_applies_manual_price_overrides():
    pack = PRODUCTS["oats"]["pack"]
    _, total, _ = planner.build_shopping_list(
        [[_meal({"oats": pack})]], REGION, overrides={"oats": 999})

    assert total == 999


def test_shopping_list_uses_region_coefficient():
    pack = PRODUCTS["oats"]["pack"]
    _, center, _ = planner.build_shopping_list([[_meal({"oats": pack})]], "center", overrides={})
    _, msk, _ = planner.build_shopping_list([[_meal({"oats": pack})]], "msk", overrides={})

    assert msk > center


def test_shopping_list_empty_plan_costs_nothing():
    items, total, consumed = planner.build_shopping_list([], REGION, overrides={})

    assert (items, total, consumed) == ([], 0, 0)


# ---------- generate_plan: структура ----------

def test_generate_plan_returns_seven_days(plan3):
    assert len(plan3["plan"]) == planner.DAYS == 7


def test_generate_plan_three_meals_per_day(plan3):
    assert [len(day) for day in plan3["plan"]] == [3] * 7


def test_generate_plan_five_meals_per_day(plan5):
    assert [len(day) for day in plan5["plan"]] == [5] * 7


def test_generate_plan_slots_follow_the_meal_order(plan5):
    pools = {mt: {m["name"] for m in MEALS[mt]} for mt in MEALS}
    for day in plan5["plan"]:
        for meal_type, meal in zip(planner.MEAL_ORDER_5, day):
            assert meal["name"] in pools[meal_type]


def test_generate_plan_returns_shopping_list_and_costs(plan3):
    assert set(plan3) >= {"plan", "items", "total", "consumed", "over_budget"}
    assert plan3["items"]
    assert plan3["total"] > 0


def test_generate_plan_total_matches_its_own_shopping_list(plan3):
    _, total, consumed = planner.build_shopping_list(plan3["plan"], REGION, overrides={})

    assert (total, consumed) == (plan3["total"], plan3["consumed"])


# ---------- generate_plan: ограничения и бюджет ----------

def test_generate_plan_respects_dietary_restrictions():
    result = _make_plan(3, goal="variety", restrictions={"vegetarian"})

    for day in result["plan"]:
        for meal in day:
            assert "vegetarian" in meal["tags"], meal["name"]


def test_generate_plan_respects_several_restrictions_at_once():
    result = _make_plan(3, goal="loss", restrictions={"gluten_free", "no_nuts"})

    for day in result["plan"]:
        for meal in day:
            assert {"gluten_free", "no_nuts"} <= set(meal["tags"]), meal["name"]


def test_generate_plan_matches_the_goal():
    result = _make_plan(3, goal="loss")

    for day in result["plan"]:
        for meal in day:
            assert "loss" in meal["goals"], meal["name"]


def test_generate_plan_with_generous_budget_is_not_over_budget():
    result = _make_plan(3, budget=10 ** 6)

    assert result["over_budget"] is False
    assert result["total"] <= 10 ** 6


def test_generate_plan_without_budget_reports_not_over_budget(plan3):
    assert plan3["over_budget"] is False


# ---------- Правила разнообразия ----------

def test_no_dish_repeats_within_one_day(plan3):
    for day in _names(plan3["plan"]):
        assert len(set(day)) == len(day), day


def test_no_dish_repeats_within_one_day_with_two_snack_slots(plan5):
    # в MEAL_ORDER_5 перекус занимает два слота — именно здесь и возможен дубль
    for day in _names(plan5["plan"]):
        assert len(set(day)) == len(day), day


def test_weekly_repeat_cap_is_honored_for_three_meals(plan3):
    counts = _counts_per_meal_type(plan3["plan"], planner.MEAL_ORDER_3)

    for meal_type, per_name in counts.items():
        cap = planner.MAX_REPEATS.get(meal_type, planner.MAX_REPEATS_DEFAULT)
        assert max(per_name.values()) <= cap, (meal_type, per_name)


def test_weekly_repeat_cap_is_honored_for_five_meals(plan5):
    counts = _counts_per_meal_type(plan5["plan"], planner.MEAL_ORDER_5)

    for meal_type, per_name in counts.items():
        cap = planner.MAX_REPEATS.get(meal_type, planner.MAX_REPEATS_DEFAULT)
        assert max(per_name.values()) <= cap, (meal_type, per_name)


def test_snacks_have_a_softer_repeat_cap_than_main_meals():
    assert planner.MAX_REPEATS["snack"] > planner.MAX_REPEATS_DEFAULT


def _counts_per_meal_type(plan: list, order: list) -> dict:
    counts: dict[str, dict[str, int]] = {}
    for day in plan:
        for meal_type, meal in zip(order, day):
            per_name = counts.setdefault(meal_type, {})
            per_name[meal["name"]] = per_name.get(meal["name"], 0) + 1
    return counts


# ---------- candidates / fits ----------

def test_fits_requires_every_restriction_tag():
    meal = {"tags": ["vegetarian"], "goals": ["loss"]}

    assert planner.fits(meal, "loss", {"vegetarian"}) is True
    assert planner.fits(meal, "loss", {"vegetarian", "gluten_free"}) is False


def test_fits_variety_goal_accepts_any_goal_tag():
    meal = {"tags": [], "goals": ["gain"]}

    assert planner.fits(meal, "variety", set()) is True
    assert planner.fits(meal, "loss", set()) is False


def test_candidates_are_filtered_by_restrictions():
    pool = planner.candidates("breakfast", "variety", {"vegetarian"})

    assert pool
    assert all("vegetarian" in m["tags"] for m in pool)


# ---------- day_macros ----------

def test_day_macros_sums_all_meals_of_the_day():
    meals = [MEALS["breakfast"][0], MEALS["lunch"][0], MEALS["dinner"][0]]
    plan_names = [[m["name"] for m in meals]]

    assert planner.day_macros(plan_names, 0) == {
        "kcal": sum(m["kcal"] for m in meals),
        "protein": sum(m["protein"] for m in meals),
        "fat": sum(m["fat"] for m in meals),
        "carbs": sum(m["carbs"] for m in meals),
    }


def test_day_macros_reads_the_requested_day_only():
    first = MEALS["breakfast"][0]
    second = MEALS["breakfast"][1]
    plan_names = [[first["name"]], [second["name"]]]

    assert planner.day_macros(plan_names, 1)["kcal"] == second["kcal"]


def test_day_macros_ignores_unknown_dish_names():
    assert planner.day_macros([["такого блюда нет"]], 0) == {
        "kcal": 0, "protein": 0, "fat": 0, "carbs": 0}


def test_day_macros_of_generated_day_is_positive(plan3):
    assert planner.day_macros(_names(plan3["plan"]), 0)["kcal"] > 0


# ---------- Поиск блюд по названию ----------

def test_meal_by_name_finds_a_known_dish():
    name = MEALS["lunch"][0]["name"]

    assert planner.meal_by_name(name)["name"] == name


def test_meal_by_name_returns_none_for_unknown():
    assert planner.meal_by_name("такого блюда нет") is None


def test_meals_from_names_drops_unknown_dishes():
    known = MEALS["breakfast"][0]["name"]
    result = planner.meals_from_names([[known, "такого блюда нет"]])

    assert [m["name"] for m in result[0]] == [known]


# ---------- swap_options ----------

def test_swap_options_never_offers_the_current_dish(plan3):
    plan_names = _names(plan3["plan"])
    current = plan_names[0][0]

    options = planner.swap_options(plan_names, 0, 0, 3, "variety", set())

    assert options
    assert current not in options


def test_swap_options_respects_the_limit(plan3):
    options = planner.swap_options(_names(plan3["plan"]), 0, 0, 3, "variety", set(), limit=2)

    assert len(options) == 2


def test_swap_options_offers_dishes_from_the_same_meal_slot(plan3):
    lunch_names = {m["name"] for m in MEALS["lunch"]}
    options = planner.swap_options(_names(plan3["plan"]), 0, 1, 3, "variety", set())

    assert options
    assert set(options) <= lunch_names


def test_swap_options_respects_restrictions(plan3):
    options = planner.swap_options(_names(plan3["plan"]), 0, 0, 3, "variety", {"vegetarian"})

    for name in options:
        assert "vegetarian" in planner.meal_by_name(name)["tags"]


def test_swap_options_returns_empty_for_slot_outside_the_day(plan3):
    assert planner.swap_options(_names(plan3["plan"]), 0, 3, 3, "variety", set()) == []


# ---------- Обратная совместимость сигнатур ----------

def _required_params(func) -> list:
    return [name for name, p in inspect.signature(func).parameters.items()
            if p.default is inspect.Parameter.empty]


def test_generate_plan_keeps_its_required_parameters():
    """Новые параметры (cooking_level, allowed_categories...) обязаны быть
    опциональными — старые вызовы без них должны продолжать работать."""
    assert _required_params(planner.generate_plan) == [
        "goal", "restrictions", "meals_per_day", "budget", "region"]


def test_swap_options_keeps_its_required_parameters():
    assert _required_params(planner.swap_options) == [
        "plan_names", "day", "slot", "meals_per_day", "goal", "restrictions"]


def test_build_shopping_list_keeps_its_required_parameters():
    assert _required_params(planner.build_shopping_list) == ["plan", "region"]


def test_candidates_keeps_its_required_parameters():
    assert _required_params(planner.candidates) == ["meal_type", "goal", "restrictions"]


def _has_cooking_params(func) -> bool:
    params = inspect.signature(func).parameters
    return "cooking_level" in params and "allowed_categories" in params


def test_generate_plan_with_default_cooking_params_matches_omitting_them():
    """Явные None в новых параметрах должны давать ровно тот же план, что и
    вызов без них — иначе старый код бота молча поменял бы поведение."""
    if not _has_cooking_params(planner.generate_plan):
        pytest.skip("cooking_level/allowed_categories ещё не добавлены в generate_plan")

    explicit = _make_plan(3, cooking_level=None, allowed_categories=None)
    implicit = _make_plan(3)

    assert _names(explicit["plan"]) == _names(implicit["plan"])
    assert explicit["total"] == implicit["total"]


def test_swap_options_with_default_cooking_params_matches_omitting_them(plan3):
    if not _has_cooking_params(planner.swap_options):
        pytest.skip("cooking_level/allowed_categories ещё не добавлены в swap_options")

    plan_names = _names(plan3["plan"])

    assert (planner.swap_options(plan_names, 0, 0, 3, "variety", set(),
                                 cooking_level=None, allowed_categories=None)
            == planner.swap_options(plan_names, 0, 0, 3, "variety", set()))


def test_meal_allowed_accepts_everything_without_preferences():
    """Без заданных предпочтений фильтр не должен отсекать ни одного блюда —
    это и есть поведение бота до появления cooking_level."""
    if not hasattr(planner, "meal_allowed"):
        pytest.skip("meal_allowed ещё не добавлен")

    for meal_type in MEALS:
        for meal in MEALS[meal_type]:
            assert planner.meal_allowed(meal, None, None) is True, meal["name"]
