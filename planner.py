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


def _pack_price(product_key: str, region: str, overrides: dict) -> float:
    """Цена упаковки: сначала смотрим ручные правки, потом справочник.

    overrides передаётся вызывающим кодом, а не читается здесь заново —
    раньше get_price_overrides() (чтение data.json с диска) вызывался на
    каждый ингредиент каждого блюда-кандидата, это тысячи чтений файла
    за один generate_plan(). С расширением базы блюд это стало заметно
    (на PythonAnywhere сетевой диск даёт задержку на порядок выше, чем
    локальный SSD)."""
    override = overrides.get(product_key)
    if override is not None:
        return float(override)
    return pack_price(product_key, region)


def fits(meal: dict, goal: str, restrictions: set) -> bool:
    if not all(r in meal["tags"] for r in restrictions):
        return False
    return goal == "variety" or goal in meal["goals"]


# Насколько человек готов возиться на кухне:
#   "simple" — только простое и быстрое, "normal" — простое любой длительности,
#   "any" (или None) — фильтр не применяется.
COOKING_LEVELS = ("simple", "normal", "any")
SIMPLE_MAX_TIME = 20

# Специи, масла, соусы и мелочь дома есть почти у всех, их не покупают ради
# одного блюда. Без этого послабления список разрешённых категорий отсекал бы
# почти всё меню: соль и масло встречаются в большинстве рецептов.
PANTRY_CATEGORIES = {"специи", "масла", "соусы", "прочее"}


def meal_allowed(meal: dict, cooking_level: str | None,
                 allowed_categories: set | None) -> bool:
    """Согласится ли человек это готовить и есть.

    Диетические ограничения сюда намеренно не входят (они в fits): вкусы и
    навыки можно ослабить ради разнообразия плана, аллергию — нельзя."""
    if cooking_level in ("simple", "normal") and meal.get("difficulty") != "easy":
        return False
    if cooking_level == "simple" and meal.get("time", 0) > SIMPLE_MAX_TIME:
        return False
    if allowed_categories is not None:
        allowed = set(allowed_categories) | PANTRY_CATEGORIES
        if any(PRODUCTS[key]["category"] not in allowed for key in meal["ingredients"]):
            return False
    return True


def _filtered(pool: list, goal: str, restrictions: set,
              cooking_level: str | None, allowed_categories: set | None) -> list:
    return [m for m in pool if fits(m, goal, restrictions)
            and meal_allowed(m, cooking_level, allowed_categories)]


def candidates(meal_type: str, goal: str, restrictions: set,
               cooking_level: str | None = None,
               allowed_categories: set | None = None,
               extra: list | None = None) -> list:
    # extra — блюда, придуманные ИИ под этого пользователя (см. _ai_top_up).
    # Дальше они ничем не отличаются от блюд базы: те же фильтры, те же уступки.
    pool = (MEALS[meal_type] + extra) if extra else MEALS[meal_type]

    def pick(g: str, cooking: str | None, cats: set | None):
        return _filtered(pool, g, restrictions, cooking, cats)

    # Уступки идут от вкусов к необходимости: сначала забываем про цель
    # (goal="variety" в fits и значит «цель не важна»), потом про навык готовки,
    # потом про список продуктов. Ограничения снимаются последними — набор
    # продуктов это «не хочу», а ограничения это аллергия и здоровье.
    return (pick(goal, cooking_level, allowed_categories)
            or pick("variety", cooking_level, allowed_categories)
            or pick("variety", None, allowed_categories)
            or pick("variety", None, None)
            or pool)


def build_shopping_list(plan: list, region: str, overrides: dict | None = None) -> tuple[list, float, float]:
    """
    Считает, сколько всего продуктов нужно на весь план.
    Возвращает (список позиций, стоимость покупки, стоимость съеденного).

    Стоимость покупки — по целым упаковкам, это реальный чек в магазине.
    Стоимость съеденного — по факту расхода: остаток упаковки (например,
    банка мёда, из которой ушло 20 г) переходит на следующие недели.

    overrides можно передать заранее (см. _pack_price) — если не передан,
    читается один раз здесь же, а не на каждый ингредиент.
    """
    if overrides is None:
        overrides = get_price_overrides()

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
        price = _pack_price(key, region, overrides)
        unit_price = price / product["pack"]
        packs = math.ceil(amount / product["pack"])
        cost = packs * price
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


def _marginal_cost(totals: dict, meal: dict, region: str, overrides: dict) -> float:
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
        extra += (packs_after - packs_before) * _pack_price(key, region, overrides)
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
          totals: dict, cheap_level: int, region: str, meal_type: str, overrides: dict):
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
        ranked = sorted(options, key=lambda m: _marginal_cost(totals, m, region, overrides))
        top = 1 if cheap_level >= 2 else 3
        return random.choice(ranked[:top])
    return random.choice(options)


def _generate_once(goal: str, restrictions: set, meals_per_day: int,
                   cheap_level: int, region: str, overrides: dict,
                   cooking_level: str | None = None,
                   allowed_categories: set | None = None,
                   extra: dict | None = None) -> list:
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
            pool = candidates(meal_type, goal, restrictions, cooking_level,
                              allowed_categories, (extra or {}).get(meal_type))
            meal = _pick(pool, counts[meal_type], last_day[meal_type], day_index,
                         day_names, totals, cheap_level, region, meal_type, overrides)
            name = meal["name"]

            counts[meal_type][name] = counts[meal_type].get(name, 0) + 1
            last_day[meal_type][name] = day_index
            for key, amount in meal["ingredients"].items():
                totals[key] = totals.get(key, 0) + amount

            day.append(meal)
            day_names.append(name)
        plan.append(day)

    return plan


# ---------- Догенерация блюд, когда своих не хватает ----------

# Сколько запросов к ИИ можно потратить на один план. Каждый — поход в сеть
# (до 25 с на провайдера, а в цепочке их три), а план собирается прямо в
# вебхуке, пока человек ждёт ответа. Четыре — это столько, сколько нужно, чтобы
# голодный приём пищи перестал повторяться: при MAX_REPEATS_DEFAULT=3 на неделю
# хватает трёх разных блюд, а тонкий пул — это обычно два.
AI_MAX_CALLS = 4

# Пул, ниже которого неделя выходит однообразной: дней в неделе семь.
# То же число, которым бот предупреждает «совсем мало вариантов».
AI_MIN_POOL = 7


def _allowed_product_keys(allowed_categories) -> list:
    allowed = set(allowed_categories) | PANTRY_CATEGORIES
    return [key for key, product in PRODUCTS.items() if product["category"] in allowed]


def _ai_top_up(order: list, goal: str, restrictions: set,
               cooking_level: str | None, allowed_categories: set | None) -> dict:
    """Просит ИИ придумать блюда для приёмов пищи, от которых после фильтров
    почти ничего не осталось. Возвращает {приём пищи: [блюда]}, в худшем случае
    пустой словарь: план обязан собраться и с недоступным ИИ."""
    if allowed_categories is None:  # продукты не ограничены — пул полный, добавлять нечего
        return {}

    sizes = {mt: len(_filtered(MEALS[mt], goal, restrictions, cooking_level, allowed_categories))
             for mt in dict.fromkeys(order)}
    thin = sorted((mt for mt, size in sizes.items() if size < AI_MIN_POOL), key=sizes.get)
    if not thin:
        return {}

    import ai_agent  # импорт здесь: без ai_fill планировщику ИИ не нужен вовсе

    keys = _allowed_product_keys(allowed_categories)
    # имена базы заняты: блюдо ищут по имени и сначала в базе, так что двойник
    # от ИИ всё равно потеряется — а рецепт человеку покажут чужой
    taken = set(MEAL_INDEX)
    extra: dict[str, list] = {}
    for i in range(AI_MAX_CALLS):
        meal_type = thin[i % len(thin)]  # первые попытки достаются самым голодным
        meal = ai_agent.generate_meal(meal_type, keys, cooking_level, goal)
        if meal is None:
            # ИИ либо недоступен (тогда каждая следующая попытка — ещё одна
            # серия таймаутов), либо ответил мимо проверок. Ждать это ещё три
            # раза внутри вебхука нельзя — собираем план из того, что есть.
            break
        # ограничения в generate_meal не передаются, поэтому теги сверяем сами:
        # вкусы и навык ради разнообразия ослабить можно, аллергию — нет
        if not _usable(meal) or meal["name"] in taken or not fits(meal, "variety", restrictions):
            continue
        taken.add(meal["name"])
        extra.setdefault(meal_type, []).append(meal)
    return extra


def _used_custom(plan: list, generated: dict) -> dict:
    """Только те придуманные блюда, что реально попали в план: остальные бот
    сохранять не должен — по названиям он потом ищет в этом же словаре."""
    if not generated:
        return {}
    return {m["name"]: generated[m["name"]] for day in plan for m in day if m["name"] in generated}


def generate_plan(goal: str, restrictions: set, meals_per_day: int,
                  budget: float | None, region: str,
                  cooking_level: str | None = None,
                  allowed_categories: set | None = None,
                  ai_fill: bool = False) -> dict:
    """
    Подбирает недельный план. Если задан бюджет, пытается уложиться в него.
    Возвращает словарь с планом, списком покупок и стоимостью.

    ai_fill — разрешить догенерацию блюд, когда своих почти не осталось.
    Придуманные блюда возвращаются отдельно в "custom_meals": в MEAL_INDEX их
    нет, поэтому без этого словаря план потом не развернуть обратно из названий.
    """
    best = None
    overrides = get_price_overrides()  # один раз на весь подбор, а не на каждый ингредиент
    order = MEAL_ORDER_5 if meals_per_day == 5 else MEAL_ORDER_3

    # ИИ спрашиваем ДО цикла: внутри это были бы десятки запросов на один план.
    extra = (_ai_top_up(order, goal, restrictions, cooking_level, allowed_categories)
             if ai_fill else {})
    generated = {m["name"]: m for meals in extra.values() for m in meals}

    for attempt in range(40):
        if budget is None:
            cheap_level = 0
        elif attempt < 5:
            cheap_level = 0
        elif attempt < 20:
            cheap_level = 1
        else:
            cheap_level = 2

        plan = _generate_once(goal, restrictions, meals_per_day, cheap_level, region,
                              overrides, cooking_level, allowed_categories, extra)
        items, total, consumed = build_shopping_list(plan, region, overrides)

        if best is None or total < best["total"]:
            best = {"plan": plan, "items": items, "total": total, "consumed": consumed,
                    "custom_meals": _used_custom(plan, generated)}

        if budget is None or total <= budget:
            return {"plan": plan, "items": items, "total": total, "consumed": consumed,
                    "over_budget": False, "custom_meals": _used_custom(plan, generated)}

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


def _usable(meal) -> bool:
    """Блюдо не из базы (придумал ИИ, пролежало в JSON рядом с планом) проверяем
    перед тем, как пустить его в дело: на ingredients держатся и чек, и КБЖУ, а
    незнакомый ключ продукта уронил бы весь пересчёт плана."""
    return (isinstance(meal, dict) and isinstance(meal.get("name"), str)
            and isinstance(meal.get("ingredients"), dict) and meal["ingredients"]
            and all(key in PRODUCTS and isinstance(amount, (int, float)) and amount > 0
                    for key, amount in meal["ingredients"].items()))


def meal_by_name(name: str, custom: dict | None = None):
    """custom — блюда, придуманные ИИ под конкретный план: их нет в базе, они
    хранятся рядом с планом. База важнее: совпали названия — блюдо берём из неё."""
    entry = MEAL_INDEX.get(name)
    if entry:
        return entry[1]
    meal = custom.get(name) if isinstance(custom, dict) else None
    return meal if _usable(meal) else None


def meals_from_names(plan_names: list, custom: dict | None = None) -> list:
    """Превращает список названий обратно в блюда — для пересчёта покупок."""
    return [[m for m in (meal_by_name(n, custom) for n in day) if m] for day in plan_names]


def rebuild_totals(plan_names: list, region: str,
                   custom: dict | None = None) -> tuple[list, int, int]:
    """Пересчитывает список покупок и стоимость после правок плана."""
    return build_shopping_list(meals_from_names(plan_names, custom), region)


def _custom_pool(plan_names: list, order: list, meal_type: str, custom: dict | None) -> list:
    """Придуманные блюда для этого приёма пищи. Своего типа они не помнят
    (в записи блюда его и нет), зато видно, в каких слотах плана они стоят —
    иначе замена в голодном слоте предлагала бы только блюда из базы."""
    if not isinstance(custom, dict):
        return []
    pool, seen = [], set()
    for names in plan_names:
        for i, name in enumerate(names):
            if i >= len(order) or order[i] != meal_type or name in MEAL_INDEX or name in seen:
                continue
            seen.add(name)
            meal = meal_by_name(name, custom)
            if meal:
                pool.append(meal)
    return pool


def swap_options(plan_names: list, day: int, slot: int, meals_per_day: int,
                 goal: str, restrictions: set, limit: int = 3,
                 cooking_level: str | None = None,
                 allowed_categories: set | None = None,
                 custom: dict | None = None) -> list:
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

    extra = _custom_pool(plan_names, order, meal_type, custom)
    pool = [m for m in candidates(meal_type, goal, restrictions, cooking_level,
                                  allowed_categories, extra)
            if m["name"] != current]
    fresh = [m for m in pool if m["name"] not in used_same_slot]
    ranked = fresh + [m for m in pool if m["name"] in used_same_slot]
    return [m["name"] for m in ranked[:limit]]


def recipe_meals_for_day(plan_names: list, day: int, custom: dict | None = None) -> list:
    """Уникальные блюда ОДНОГО дня плана, у которых есть рецепт — в порядке появления.
    Раньше показывали рецепты сразу за всю неделю — длинный нечитаемый список."""
    seen, result = set(), []
    for name in plan_names[day]:
        meal = meal_by_name(name, custom)
        if meal and "recipe" in meal and name not in seen:
            seen.add(name)
            result.append(name)
    return result


def format_recipe(name: str, custom: dict | None = None) -> str:
    from products import PRODUCTS, format_amount

    meal = meal_by_name(name, custom)
    recipe = meal.get("recipe") if meal else None
    if not isinstance(recipe, dict):
        return "Для этого блюда рецепт не нужен — всё готовится за пару минут."

    lines = [f"👨‍🍳 *{name}*", f"⏱ Время: около {recipe.get('time', meal.get('time', 0))} мин"]
    if "kcal" in meal:
        lines.append(f"🔥 {meal['kcal']} ккал · Б {meal.get('protein', 0)} "
                      f"Ж {meal.get('fat', 0)} У {meal.get('carbs', 0)}")
    lines.append("")
    lines.append("*Понадобится на порцию:*")
    for key, amount in meal["ingredients"].items():
        lines.append(f"• {PRODUCTS[key]['name']} — {format_amount(key, amount)}")
    lines.append("")
    lines.append("*Приготовление:*")
    for i, step in enumerate(recipe.get("steps") or [], start=1):
        lines.append(f"{i}. {step}")
    return "\n".join(lines)


def day_macros(plan_names: list, day: int, custom: dict | None = None) -> dict:
    """Суммарное КБЖУ за день (0, если у блюд нет данных о питательности)."""
    totals = {"kcal": 0, "protein": 0, "fat": 0, "carbs": 0}
    for name in plan_names[day]:
        meal = meal_by_name(name, custom)
        if not meal:
            continue
        for key in totals:
            totals[key] += meal.get(key, 0)
    return totals


def format_day(plan_names: list, day: int, meals_per_day: int,
               custom: dict | None = None) -> str:
    """Один день плана — компактно, вместо всей недели сразу."""
    from meals_data import MEAL_TYPE_LABELS

    order = MEAL_ORDER_5 if meals_per_day == 5 else MEAL_ORDER_3
    lines = [f"📅 *День {day + 1} из {DAYS}*", ""]
    for meal_type, name in zip(order, plan_names[day]):
        meal = meal_by_name(name, custom)
        mark = " 👨‍🍳" if meal and "recipe" in meal else ""
        kcal_part = f" ({meal['kcal']} ккал)" if meal and "kcal" in meal else ""
        lines.append(f"{MEAL_TYPE_LABELS[meal_type]}: {name}{kcal_part}{mark}")

    macros = day_macros(plan_names, day, custom)
    if macros["kcal"]:
        lines.append("")
        lines.append(f"🔥 *{macros['kcal']} ккал за день* · Б {macros['protein']} "
                      f"Ж {macros['fat']} У {macros['carbs']}")
    return "\n".join(lines)
