"""
Логика планирования: подбор блюд под цель, ограничения и бюджет,
расчёт стоимости и сборка списка покупок.
"""

import math
import random

from meals_data import MEALS
from products import PRODUCTS, format_amount, pack_price
from storage import get_price_overrides

DAYS = 7
MEAL_ORDER_3 = ["breakfast", "lunch", "dinner"]
MEAL_ORDER_5 = ["breakfast", "snack", "lunch", "snack", "dinner"]


def _pack_price(product_key: str, region: str) -> float:
    """Цена упаковки: сначала смотрим ручные правки, потом справочник."""
    override = get_price_overrides().get(product_key)
    if override is not None:
        return float(override)
    return pack_price(product_key, region)


def fits(meal: dict, goal: str, restrictions: set) -> bool:
    if not all(r in meal["tags"] for r in restrictions):
        return False
    return goal == "variety" or goal in meal["goals"]


def candidates(meal_type: str, goal: str, restrictions: set) -> list:
    pool = MEALS[meal_type]
    strict = [m for m in pool if fits(m, goal, restrictions)]
    if strict:
        return strict
    # если под цель ничего не нашлось — соблюдаем хотя бы ограничения
    loose = [m for m in pool if all(r in m["tags"] for r in restrictions)]
    return loose or pool


def build_shopping_list(plan: list, region: str) -> tuple[list, float, float]:
    """
    Считает, сколько всего продуктов нужно на весь план.
    Возвращает (список позиций, стоимость покупки, стоимость съеденного).

    Стоимость покупки — по целым упаковкам, это реальный чек в магазине.
    Стоимость съеденного — по факту расхода: остаток упаковки (например,
    банка мёда, из которой ушло 20 г) переходит на следующие недели.
    """
    totals: dict[str, float] = {}
    for day in plan:
        for meal in day:
            for key, amount in meal["ingredients"].items():
                totals[key] = totals.get(key, 0) + amount

    items = []
    grand_total = 0.0
    consumed_total = 0.0
    for key, amount in totals.items():
        product = PRODUCTS[key]
        unit_price = _pack_price(key, region) / product["pack"]
        packs = math.ceil(amount / product["pack"])
        cost = packs * _pack_price(key, region)
        grand_total += cost
        consumed_total += amount * unit_price
        items.append({
            "key": key,
            "name": product["name"],
            "amount_text": format_amount(key, amount),
            "packs": packs,
            "cost": round(cost),
        })

    items.sort(key=lambda i: -i["cost"])
    return items, round(grand_total), round(consumed_total)


def _marginal_cost(totals: dict, meal: dict, region: str) -> float:
    """
    Сколько ДОБАВИТСЯ к чеку, если включить это блюдо.
    Если продукт уже куплен и остатка в упаковке хватает — добавка нулевая.
    Именно так и экономят в жизни: берут блюда из уже имеющихся продуктов.
    """
    extra = 0.0
    for key, amount in meal["ingredients"].items():
        product = PRODUCTS[key]
        was = totals.get(key, 0)
        packs_before = math.ceil(was / product["pack"]) if was else 0
        packs_after = math.ceil((was + amount) / product["pack"])
        extra += (packs_after - packs_before) * _pack_price(key, region)
    return extra


# Сколько раз одно блюдо может встретиться за неделю.
# Перекусов за неделю вдвое больше (два слота в день), да и повторить банан
# не так утомительно, как седьмой раз тот же ужин — поэтому лимит мягче.
MAX_REPEATS = {"snack": 5}
MAX_REPEATS_DEFAULT = 3

# Минимальный разрыв между повторами: 2 = через день (дни 1-3-5).
MIN_GAP_DAYS = {"snack": 1}
MIN_GAP_DEFAULT = 2


def _pick(pool: list, counts: dict, last_day: dict, day: int, day_names: list,
          totals: dict, cheap_level: int, region: str, meal_type: str):
    """
    Выбирает блюдо с учётом правил разнообразия.
    Ограничения снимаются по очереди, только если иначе выбрать не из чего:
      1) не чаще MAX_REPEATS раз за неделю, не подряд, не дважды за день;
      2) если не осталось вариантов — разрешаем ставить чаще;
      3) в самом крайнем случае — берём что есть.
    """
    max_repeats = MAX_REPEATS.get(meal_type, MAX_REPEATS_DEFAULT)
    min_gap = MIN_GAP_DAYS.get(meal_type, MIN_GAP_DEFAULT)

    def allowed(strict: bool):
        result = []
        for m in pool:
            name = m["name"]
            if name in day_names:                        # не дважды в один день
                continue
            if strict:
                if counts.get(name, 0) >= max_repeats:   # лимит на неделю
                    continue
                if day - last_day.get(name, -99) < min_gap:  # разрыв между повторами
                    continue
            result.append(m)
        return result

    options = allowed(strict=True) or allowed(strict=False) or pool

    if cheap_level >= 1:
        ranked = sorted(options, key=lambda m: _marginal_cost(totals, m, region))
        top = 1 if cheap_level >= 2 else 3
        return random.choice(ranked[:top])
    return random.choice(options)


def _generate_once(goal: str, restrictions: set, meals_per_day: int,
                   cheap_level: int, region: str) -> list:
    """
    cheap_level: 0 — свободный подбор, 1 — умеренная экономия, 2 — жёсткая.
    Правила разнообразия действуют на всех уровнях: даже в самом экономном
    режиме одно блюдо не может занять всю неделю.
    """
    order = MEAL_ORDER_5 if meals_per_day == 5 else MEAL_ORDER_3
    plan = []
    totals: dict[str, float] = {}
    # счётчики ведём отдельно для каждого приёма пищи
    counts = {mt: {} for mt in set(order)}
    last_day = {mt: {} for mt in set(order)}

    for day_index in range(DAYS):
        day = []
        day_names: list[str] = []
        for meal_type in order:
            pool = candidates(meal_type, goal, restrictions)
            meal = _pick(pool, counts[meal_type], last_day[meal_type], day_index,
                         day_names, totals, cheap_level, region, meal_type)
            name = meal["name"]

            counts[meal_type][name] = counts[meal_type].get(name, 0) + 1
            last_day[meal_type][name] = day_index
            for key, amount in meal["ingredients"].items():
                totals[key] = totals.get(key, 0) + amount

            day.append(meal)
            day_names.append(name)
        plan.append(day)

    return plan


def generate_plan(goal: str, restrictions: set, meals_per_day: int,
                  budget: float | None, region: str) -> dict:
    """
    Подбирает недельный план. Если задан бюджет, пытается уложиться в него.
    Возвращает словарь с планом, списком покупок и стоимостью.
    """
    best = None

    for attempt in range(40):
        if budget is None:
            cheap_level = 0
        elif attempt < 5:
            cheap_level = 0
        elif attempt < 20:
            cheap_level = 1
        else:
            cheap_level = 2

        plan = _generate_once(goal, restrictions, meals_per_day, cheap_level, region)
        items, total, consumed = build_shopping_list(plan, region)

        if best is None or total < best["total"]:
            best = {"plan": plan, "items": items, "total": total, "consumed": consumed}

        if budget is None or total <= budget:
            return {"plan": plan, "items": items, "total": total,
                    "consumed": consumed, "over_budget": False}

    best["over_budget"] = budget is not None and best["total"] > budget
    return best


def format_plan(plan_names: list, meals_per_day: int) -> str:
    """plan_names — список дней, в каждом дне список названий блюд."""
    from meals_data import MEAL_TYPE_LABELS

    order = MEAL_ORDER_5 if meals_per_day == 5 else MEAL_ORDER_3
    lines = []
    for i, day in enumerate(plan_names, start=1):
        lines.append(f"📅 *День {i}*")
        for meal_type, name in zip(order, day):
            lines.append(f"{MEAL_TYPE_LABELS[meal_type]}: {name}")
        lines.append("")
    return "\n".join(lines)


def format_shopping_list(items: list, bought: set) -> str:
    lines = ["🛒 *Список покупок на неделю*", ""]
    remaining = 0
    for i, item in enumerate(items):
        done = i in bought
        box = "✅" if done else "⬜️"
        text = f"{box} {item['name']} — {item['amount_text']} ({item['packs']} уп. ≈ {item['cost']} ₽)"
        if done:
            text = f"{box} ~{item['name']}~ — {item['packs']} уп."
        else:
            remaining += item["cost"]
        lines.append(text)

    lines.append("")
    lines.append(f"Осталось купить примерно на *{round(remaining)} ₽*")
    return "\n".join(lines)


# ---------- Работа с готовым планом (замена блюд, рецепты) ----------

MEAL_INDEX = {m["name"]: (mtype, m) for mtype in MEALS for m in MEALS[mtype]}


def meal_by_name(name: str):
    entry = MEAL_INDEX.get(name)
    return entry[1] if entry else None


def meals_from_names(plan_names: list) -> list:
    """Превращает список названий обратно в блюда — для пересчёта покупок."""
    return [[meal_by_name(n) for n in day if meal_by_name(n)] for day in plan_names]


def rebuild_totals(plan_names: list, region: str) -> tuple[list, int, int]:
    """Пересчитывает список покупок и стоимость после правок плана."""
    return build_shopping_list(meals_from_names(plan_names), region)


def swap_options(plan_names: list, day: int, slot: int, meals_per_day: int,
                 goal: str, restrictions: set, limit: int = 3) -> list:
    """
    Подбирает альтернативы для конкретного блюда в плане.
    Возвращает список названий: подходят под цель и ограничения,
    не совпадают с текущим блюдом и не повторяют соседние дни.
    """
    order = MEAL_ORDER_5 if meals_per_day == 5 else MEAL_ORDER_3
    if slot >= len(order):
        return []
    meal_type = order[slot]
    current = plan_names[day][slot]

    # что уже стоит в этом же приёме пищи в другие дни — предлагаем в последнюю очередь
    used_same_slot = {d[slot] for i, d in enumerate(plan_names) if i != day and slot < len(d)}

    pool = [m for m in candidates(meal_type, goal, restrictions) if m["name"] != current]
    fresh = [m for m in pool if m["name"] not in used_same_slot]
    ranked = fresh + [m for m in pool if m["name"] in used_same_slot]
    return [m["name"] for m in ranked[:limit]]


def recipe_meals(plan_names: list) -> list:
    """Уникальные блюда плана, у которых есть рецепт — в порядке появления."""
    seen, result = set(), []
    for day in plan_names:
        for name in day:
            meal = meal_by_name(name)
            if meal and "recipe" in meal and name not in seen:
                seen.add(name)
                result.append(name)
    return result


def format_recipe(name: str) -> str:
    from products import PRODUCTS, format_amount

    meal = meal_by_name(name)
    if not meal or "recipe" not in meal:
        return "Для этого блюда рецепт не нужен — всё готовится за пару минут."

    recipe = meal["recipe"]
    lines = [f"👨‍🍳 *{name}*", f"⏱ Время: около {recipe['time']} мин", "", "*Понадобится на порцию:*"]
    for key, amount in meal["ingredients"].items():
        lines.append(f"• {PRODUCTS[key]['name']} — {format_amount(key, amount)}")
    lines.append("")
    lines.append("*Приготовление:*")
    for i, step in enumerate(recipe["steps"], start=1):
        lines.append(f"{i}. {step}")
    return "\n".join(lines)


def format_day(plan_names: list, day: int, meals_per_day: int) -> str:
    """Один день плана — компактно, вместо всей недели сразу."""
    from meals_data import MEAL_TYPE_LABELS

    order = MEAL_ORDER_5 if meals_per_day == 5 else MEAL_ORDER_3
    lines = [f"📅 *День {day + 1} из {DAYS}*", ""]
    for meal_type, name in zip(order, plan_names[day]):
        meal = meal_by_name(name)
        mark = " 👨‍🍳" if meal and "recipe" in meal else ""
        lines.append(f"{MEAL_TYPE_LABELS[meal_type]}: {name}{mark}")
    return "\n".join(lines)
